import sys
import os
import requests
import json
from datetime import datetime, timezone
import urllib.parse
import time
import subprocess
import traceback
import urllib3
import argparse
from bs4 import BeautifulSoup

# ----------------------------------------START CONFIGURATION----------------------------------------

POLARION_BASE_URL = "https://application-lifecycle-el.abb.com/polarion/rest/v1"
CURL_USER_AGENT = "curl/8.12.1"

VERIFY_SSL_REQUESTS = False

POLLING_INTERVAL_SECONDS = 300
LOG_LEVEL_THRESHOLD = "DEBUG"

POLLER_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR_PATH = os.path.abspath(os.path.join(POLLER_SCRIPT_DIR, '..', 'Config'))
REPORT_DIR_NAME = "report"
REPORT_DIR_PATH = os.path.abspath(os.path.join(POLLER_SCRIPT_DIR, '..', '..', REPORT_DIR_NAME))
CONFIG_JSON_FILENAME = "configTest.json"

TESTRUNNER_SCRIPT_NAME = "TestRunner.py"
SUBPROCESS_TIMEOUT_SECONDS = None 
EXECUTOR_LINK_ROLE = "executed_by"

STATUS_TR_LOCKED = "closed"
STATUS_TR_UNLOCKED = "open"

LOOP_MODE = False
ALWAYS_CLOSE_WIN_SAM = True

# ----------------------------------------END CONFIGURATION----------------------------------------

if VERIFY_SSL_REQUESTS is False:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def start_test_timer():
    _test_start_time = time.monotonic()
    return _test_start_time

def get_test_duration(_test_start_time):
    duration = time.monotonic() - _test_start_time
    return duration

def get_log_level_priority(level_name):
    priorities = {
        "DEBUG": 1, "INFO": 2, "WARNING": 3, "ERROR": 4, "CRITICAL": 5
    }
    return priorities.get(level_name.upper(), 0)

def log_message(level, message):
    if get_log_level_priority(level) >= get_log_level_priority(LOG_LEVEL_THRESHOLD):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] POLLER [{level.upper()}]: {message}")

def get_polarion_api_headers(pat_token, content_type="application/json"):
    headers = {
        "Authorization": f"Bearer {pat_token}",
        "Accept": "application/json",
        "User-Agent": CURL_USER_AGENT
    }
    if content_type: 
        headers["Content-Type"] = content_type
    return headers

def get_polarion_test_run_details(project_id, full_test_run_id_or_short_id, pat_token):
    if '/' in full_test_run_id_or_short_id:
        if not full_test_run_id_or_short_id.startswith(project_id + '/'):
            log_message("error", f"    get_polarion_test_run_details: Full ID '{full_test_run_id_or_short_id}' does not match project '{project_id}'.")
            return None
        actual_test_run_id_for_url = full_test_run_id_or_short_id.split('/')[-1]
        id_for_logging = full_test_run_id_or_short_id
    else:
        actual_test_run_id_for_url = full_test_run_id_or_short_id
        id_for_logging = f"{project_id}/{full_test_run_id_or_short_id}"
        
    get_url = f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_test_run_id_for_url}?fields[testruns]=status,id,title"

    headers = get_polarion_api_headers(pat_token)
    response = None
    try:
        response = requests.get(get_url, headers=headers, timeout=60, verify=VERIFY_SSL_REQUESTS)
        if response.status_code == 200:
            tr_data = response.json().get("data")
            if tr_data:
                return tr_data
            else:
                log_message("error", f"    Test Run '{id_for_logging}' data block not found in response: {response.text[:500]}")
                return None
        elif response.status_code == 404:
            log_message("warning", f"    Test Run '{id_for_logging}' not found (404).")
            return None
        else:
            response.raise_for_status()
            return None
    except requests.exceptions.HTTPError as e_http:
        log_message("error", f"    Failed to get details for TR '{id_for_logging}'. S:{e_http.response.status_code}, D:{e_http.response.text[:500]}")
    except Exception as e:
        log_message("error", f"    Exception getting details for TR '{id_for_logging}': {e}")
        if response is not None: log_message("error", f"  Response text on exception: {response.text[:400]}")
    return None


def set_polarion_test_run_status(project_id, full_test_run_id, new_status_id_string, pat_token):
    if '/' not in full_test_run_id:
        log_message("warning", f"    set_polarion_test_run_status: full_test_run_id '{full_test_run_id}' non sembra nel formato ProjectID/ShortID. Usando '{project_id}/{full_test_run_id}' per il payload.")
        actual_test_run_id_for_url = full_test_run_id
        payload_id = f"{project_id}/{full_test_run_id}"
    else:
        actual_test_run_id_for_url = full_test_run_id.split('/')[-1]
        payload_id = full_test_run_id

    log_message("info", f"    Attempting to set status of TR '{payload_id}' to '{new_status_id_string}'.")
    patch_url = f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_test_run_id_for_url}"

    payload = {
        "data": {
            "type": "testruns",
            "id": payload_id,
            "attributes": {
                "status": new_status_id_string
            }
        }
    }

    headers = get_polarion_api_headers(pat_token)
    response = None
    try:
        response = requests.patch(patch_url, headers=headers, json=payload, timeout=60, verify=VERIFY_SSL_REQUESTS)

        if response.status_code == 200 or response.status_code == 204:
            log_message("info", f"    Successfully set status of TR '{payload_id}' to '{new_status_id_string}'. Status Code: {response.status_code}")
            return True
        else:
            log_message("error", f"    Failed to set status for TR '{payload_id}'. S:{response.status_code}, D:{response.text[:500]}")
            return False
    except Exception as e:
        log_message("error", f"    Exception setting status for TR '{payload_id}': {e}")
        if response is not None: log_message("error", f"  Response text on exception: {response.text[:400]}")
        return False

def get_testrun_ready_query(project_id):
    base_query = f"project.id:{project_id} AND type:automated AND status:{STATUS_TR_UNLOCKED}"
    return base_query

def find_test_runs_to_process(project_id, pat_token):
    current_testrun_ready_query = get_testrun_ready_query(project_id)
    log_message("info", f"Searching for ready Test Runs (Project: '{project_id}'). Raw Lucene Query: '{current_testrun_ready_query}'")
    fields_list_value = "id,title,status"
    encoded_lucene_query_value = urllib.parse.quote(current_testrun_ready_query)
    query_string_manual = f"fields[testruns]={fields_list_value}&query={encoded_lucene_query_value}"
    full_url = f"{POLARION_BASE_URL}/projects/{project_id}/testruns?{query_string_manual}"

    ids = []
    response = None
    api_headers = get_polarion_api_headers(pat_token)
    try:
        response = requests.get(full_url, headers=api_headers, timeout=60, verify=VERIFY_SSL_REQUESTS)

        if response.headers.get('Content-Type', '').lower().startswith('text/html'):
            log_message("error", f"Expected JSON but received HTML when finding Test Runs. Possible SSO redirect or PAT issue. Response snippet: {response.text[:500]}")
            return []

        response.raise_for_status()
        data = response.json()
        test_run_items = data.get("data", [])

        if isinstance(test_run_items, list):
            for item in test_run_items:
                tr_id_val = item.get("id")
                if tr_id_val:
                    ids.append(tr_id_val)
                else:
                    tr_id_val_attr = item.get("attributes", {}).get("id")
                    if tr_id_val_attr:
                        full_id_constructed = f"{project_id}/{tr_id_val_attr}"
                        log_message("warning", f"Test Run ID found in attributes: {tr_id_val_attr}. Using constructed full ID: {full_id_constructed}.")
                        ids.append(full_id_constructed)
                    else:
                        log_message("warning", f"Skipping malformed test run item in response (ID not found): {item}")
            log_message("info", f"Found {len(ids)} ready TRs: {ids}")
        elif test_run_items is None and isinstance(data, dict) and data.get("data") == []:
            log_message("info", "Found 0 ready TRs (API returned 'data': []).")
        else:
            log_message("warning", f"Expected list for 'data', got: {type(test_run_items)}. Data: {str(data)[:500]}")

    except requests.exceptions.HTTPError as e_http:
        text_err = e_http.response.text[:500] if e_http.response is not None else 'N/A'
        log_message("error", f"HTTPError searching TRs (Status {e_http.response.status_code if e_http.response else 'N/A'}): {text_err}")
    except requests.exceptions.JSONDecodeError as e_json:
        log_message("error", f"JSONDecodeError searching TRs: {e_json}. Response text: {response.text[:1000]}")
    except Exception as e_gen:
        log_message("error", f"Exception searching TRs: {e_gen}\n{traceback.format_exc()}")
    return ids

def fetch_test_cases_from_polarion_test_run(project_id, full_test_run_id, pat_token):
    actual_test_run_id_for_url = full_test_run_id.split('/')[-1] if '/' in full_test_run_id else full_test_run_id
    log_message("info", f"Fetching Test Cases (using fields[testrecords]=@all) for TR ID: {full_test_run_id} (using ID '{actual_test_run_id_for_url}' for URL) in project {project_id}...")
    waiting_test_record_details = []
    endpoint_url = (
        f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_test_run_id_for_url}/testrecords"
        f"?include=testCase&fields[workitems]=id&fields[testrecords]=@all"
    )
    response = None
    api_headers = get_polarion_api_headers(pat_token)
    try:
        response = requests.get(endpoint_url, headers=api_headers, timeout=60, verify=VERIFY_SSL_REQUESTS)

        if response.headers.get('Content-Type', '').lower().startswith('text/html'):
            log_message("error", f"Expected JSON but received HTML when fetching test cases. Possible SSO redirect. Response snippet: {response.text[:500]}")
            return []

        response.raise_for_status()
        response_data = response.json()

        test_records_data = response_data.get("data", [])
        included_items = response_data.get("included", [])
        workitem_id_map = {}
        for item in included_items:
            if item.get("type") in ["workitems", "workitem"]:
                full_wi_id = item.get("id")
                item_attributes = item.get("attributes", {})
                if full_wi_id:
                    local_tc_id = item_attributes.get("id", full_wi_id.split('/')[-1] if '/' in full_wi_id else full_wi_id)
                    workitem_id_map[full_wi_id] = local_tc_id

        for record_item in test_records_data:
            record_id_full = record_item.get('id')
            if not record_id_full:
                log_message("warning", f"    Skipping record item with no ID: {record_item}")
                continue

            record_attributes = record_item.get("attributes")
            is_waiting = False
            if record_attributes:
                if record_attributes.get("result") is None:
                    is_waiting = True
            else:
                log_message("warning", f"    Record (ID: {record_id_full}) has no attributes. Cannot determine if 'waiting'. Skipping.")
                continue

            if is_waiting:
                tc_relationship_data = record_item.get("relationships", {}).get("testCase", {}).get("data")
                if tc_relationship_data and tc_relationship_data.get("type") in ["workitems", "workitem"]:
                    full_tc_id_rel = tc_relationship_data.get("id")
                    if full_tc_id_rel:
                        local_id = workitem_id_map.get(full_tc_id_rel, full_tc_id_rel.split('/')[-1])

                        iteration_str = None
                        if record_attributes and record_attributes.get("iteration") is not None:
                            iteration_str = str(record_attributes.get("iteration"))
                        else:
                            record_id_parts = record_id_full.split('/')
                            if len(record_id_parts) >= 5:
                                iteration_candidate = record_id_parts[-1]
                                try:
                                    int(iteration_candidate)
                                    iteration_str = iteration_candidate
                                except ValueError:
                                    log_message("warning", f"    Could not parse iteration index from record ID component '{iteration_candidate}' for record '{record_id_full}'.")

                        if local_id and iteration_str is not None:
                            already_added = any(
                                detail["tc_id"] == local_id and detail["iteration"] == iteration_str
                                for detail in waiting_test_record_details
                            )
                            if not already_added:
                                waiting_test_record_details.append({"tc_id": local_id, "iteration": iteration_str})
                        elif not local_id:
                            log_message("warning", f"    Could not determine local_id for full_tc_id_rel '{full_tc_id_rel}' from record '{record_id_full}'.")
                        elif iteration_str is None:
                             log_message("warning", f"    Could not determine iteration for TC '{local_id}' from record '{record_id_full}'.")

        log_message("info", f"Found {len(waiting_test_record_details)} 'waiting' TC/iteration pairs for TR '{full_test_run_id}': {waiting_test_record_details}")
    except requests.exceptions.JSONDecodeError as e_json:
        log_message("error", f"JSONDecodeError fetching test cases for TR '{full_test_run_id}': {e_json}. Response text: {response.text[:1000]}")
    except Exception as e:
        log_message("error", f"Error in fetch_test_cases for TR '{full_test_run_id}': {e}\n{traceback.format_exc()}")
        if response is not None: log_message("error", f"Response text on error: {response.text[:1000]}")
    return waiting_test_record_details

def get_existing_attachments_for_test_record(
    project_id,
    full_test_run_id,
    test_case_project_id,
    local_tc_id,
    iteration_index_str,
    pat_token
):
    
    actual_tr_id = full_test_run_id.split('/')[-1]
    attachments_url = (
        f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_tr_id}"
        f"/testrecords/{test_case_project_id}/{local_tc_id}/{iteration_index_str}/attachments"
    )
    
    log_message("info", f"    Fetching existing attachments for TC '{local_tc_id}', Iteration '{iteration_index_str}'...")
    headers = get_polarion_api_headers(pat_token)
    try:
        response = requests.get(attachments_url, headers=headers, timeout=60, verify=VERIFY_SSL_REQUESTS)
        if response.status_code == 200:
            attachments = response.json().get("data", [])
            log_message("info", f"      Found {len(attachments)} existing attachments.")
            return attachments
        else:
            log_message("error", f"      Failed to get existing attachments. S:{response.status_code}, D:{response.text[:500]}")
            return []
    except Exception as e:
        log_message("error", f"      Exception getting existing attachments: {e}")
        return []

def delete_attachments_from_test_record(
    project_id,
    full_test_run_id,
    test_case_project_id,
    local_tc_id,
    iteration_index_str,
    attachments_to_delete,
    pat_token
):
    if not attachments_to_delete:
        return True

    actual_tr_id = full_test_run_id.split('/')[-1]
    delete_url = (
        f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_tr_id}"
        f"/testrecords/{test_case_project_id}/{local_tc_id}/{iteration_index_str}/attachments"
    )

    payload = {
        "data": [
            {"type": att.get("type", "testrecord_attachments"), "id": att.get("id")}
            for att in attachments_to_delete if att.get("id")
        ]
    }

    if not payload["data"]:
        log_message("warning", "      Attachment list provided, but no valid IDs found to delete.")
        return True
    
    log_message("info", f"    Deleting {len(payload['data'])} existing attachments for TC '{local_tc_id}', Iteration '{iteration_index_str}'...")
    headers = get_polarion_api_headers(pat_token)
    try:
        response = requests.delete(delete_url, headers=headers, json=payload, timeout=60, verify=VERIFY_SSL_REQUESTS)
        if response.status_code == 204:
            log_message("info", "      Successfully deleted existing attachments.")
            return True
        else:
            log_message("error", f"      Failed to delete attachments. S:{response.status_code}, D:{response.text[:500]}")
            return False
    except Exception as e:
        log_message("error", f"      Exception deleting attachments: {e}")
        return False

def extract_test_results_from_html_report(html_report_path, test_time):
    results = {
        "outcome": "failed",
        "duration_seconds": 0, 
        "executed_timestamp_utc_iso": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "comment_text": "HTML report parsing resulted in default values."
    }
    try:
        if not os.path.exists(html_report_path):
            log_message("error", f"        HTML report file not found for extraction: {html_report_path}")
            results["comment_text"] = "HTML report file not found for result extraction."
            return results

        with open(html_report_path, 'r', encoding='iso-8859-1') as f_html:
            soup = BeautifulSoup(f_html, 'html.parser')

        comment_parts = []

        uut_result_tag = soup.find('td', class_='hdr_name', string='UUT Result: ')
        if uut_result_tag and uut_result_tag.find_next_sibling('td', class_='hdr_value'):
            uut_result_value_tag = uut_result_tag.find_next_sibling('td', class_='hdr_value')
            uut_result_span = uut_result_value_tag.find('span')
            if uut_result_span and uut_result_span.string:
                outcome_raw = uut_result_span.string.strip().lower()
                if outcome_raw == "passed":
                    results["outcome"] = "passed"
                elif outcome_raw == "failed":
                    results["outcome"] = "failed"
                else:
                    results["outcome"] = "blocked"
                    log_message("warning", f"        UUT Result from HTML was '{outcome_raw}', which is not a standard outcome. Setting status to 'blocked'.")
                    comment_parts.append(f"TestStand UUT Result was '{uut_result_span.string.strip()}', setting status to blocked.")
                
                if results["outcome"] != "blocked":
                    comment_parts.append(f"TestStand UUT Result from HTML: {uut_result_span.string.strip()}")
            else:
                results["outcome"] = "blocked"
                comment_parts.append("UUT Result value tag was found but content is empty in HTML. Setting status to blocked.")
                log_message("warning", "        UUT Result value tag was found but content is empty in HTML. Setting status to blocked.")
        else:
            results["outcome"] = "null"
            comment_parts.append("UUT Result tag not found in HTML. Setting status to waiting.")
            log_message("warning", "        UUT Result not found in HTML report. Setting status to waiting.")


        date_tag = soup.find('td', class_='hdr_name', string='Date: ')
        time_tag = soup.find('td', class_='hdr_name', string='Time: ')

        date_str = None
        time_str = None

        if date_tag and date_tag.find_next_sibling('td', class_='hdr_value'):
            date_str = date_tag.find_next_sibling('td', class_='hdr_value').string.strip()
        if time_tag and time_tag.find_next_sibling('td', class_='hdr_value'):
            time_str = time_tag.find_next_sibling('td', class_='hdr_value').string.strip()

        executed_dt_utc_naive_for_iso = datetime.now(timezone.utc).replace(tzinfo=None)
        if date_str and time_str:
            try:
                parts = date_str.split()
                if len(parts) >= 3:
                    day = parts[-3] if len(parts) >=3 else parts[-2]
                    month_name_it = parts[-2] if len(parts) >=3 else parts[-1]
                    year = parts[-1]

                    month_it_to_num = {
                        "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
                        "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
                        "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
                    }
                    month_num_str = month_it_to_num.get(month_name_it.lower())
                    if month_num_str:
                        formatted_date_str = f"{day}/{month_num_str}/{year}"
                        dt_naive_from_html = datetime.strptime(f"{formatted_date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                        executed_dt_utc_naive_for_iso = dt_naive_from_html.astimezone(timezone.utc).replace(tzinfo=None)
                    else:
                        log_message("warning", f"        Could not parse month '{month_name_it}' from HTML Date: {date_str}. Using current UTC naive time.")
                else:
                    log_message("warning", f"        Could not parse HTML Date format: {date_str}. Using current UTC naive time.")
            except ValueError as e_dt:
                log_message("warning", f"        Could not parse Date/Time '{date_str} {time_str}' from HTML: {e_dt}. Using current UTC naive time.")
        else:
            log_message("warning", "        Date or Time not found in HTML report. Using current UTC naive time.")
        results["executed_timestamp_utc_iso"] = executed_dt_utc_naive_for_iso.isoformat() + "Z"

        test_name_tag = soup.find('td', class_='label', string='Test:')

        results["duration_seconds"] = test_time

        if comment_parts:
            results["comment_text"] = '\n'.join(comment_parts)
        else:
            results["comment_text"] = "Test results extracted from HTML report."

        log_message("info", f"        Extracted results from HTML '{os.path.basename(html_report_path)}': Outcome={results['outcome']}, Executed={results['executed_timestamp_utc_iso']}")
        return results

    except Exception as e_t:
        log_message("error", f"        Generic error extracting results from HTML '{html_report_path}': {e_t}\n{traceback.format_exc()}")
        results["comment_text"] = f"Generic HTML extraction error: {e_t}"
        results["outcome"] = "null"
        return results

def run_local_testrunner_script(runner_script_name_with_ext, base_path_for_runner):
    script_full_path = os.path.join(base_path_for_runner, runner_script_name_with_ext)
    if not os.path.exists(script_full_path):
        log_message("error", f"    TestRunner script '{script_full_path}' not found."); return -999, "", ""

    cmd_args = [sys.executable, script_full_path]

    log_message("info", f"    Starting TestRunner: '{' '.join(cmd_args)}' (CWD: '{base_path_for_runner}')...")
    env = os.environ.copy()
    try:
        process_result = subprocess.run(
            cmd_args,
            cwd=base_path_for_runner,
            capture_output=True, text=True, check=False,
            encoding='utf-8', errors='replace',
            timeout=SUBPROCESS_TIMEOUT_SECONDS,
            env=env
        )
        log_message("info", f"    {runner_script_name_with_ext} script finished. Exit Code from script: {process_result.returncode}.")
        return process_result.returncode, process_result.stdout, process_result.stderr
    except subprocess.TimeoutExpired:
        log_message("error", f"    TestRunner script '{script_full_path}' timed out after {SUBPROCESS_TIMEOUT_SECONDS} seconds.")
        return -998, "", "TimeoutExpired"
    except Exception as e:
        log_message("error", f"    Exception running TestRunner script '{script_full_path}': {e}"); return -997, "", str(e)

def patch_polarion_test_record(
    project_id,
    full_test_run_id,
    test_case_project_id,
    local_tc_id,
    iteration_index_str,
    test_results,
    pat_token
    ):

    actual_tr_id = full_test_run_id.split('/')[-1]
    full_test_record_id = f"{project_id}/{actual_tr_id}/{test_case_project_id}/{local_tc_id}/{iteration_index_str}"
    patch_url = f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_tr_id}/testrecords/{test_case_project_id}/{local_tc_id}/{iteration_index_str}"

    log_message("info", f"    Patching Test Record '{full_test_record_id}' for TC '{local_tc_id}' Iteration '{iteration_index_str}'")

    attributes_to_patch = {
        "result": test_results["outcome"],
        "executed": test_results["executed_timestamp_utc_iso"],
        "duration": test_results["duration_seconds"],
        "comment": {
            "type": "text/html",
            "value": test_results["comment_text"]
        }
    }

    payload = {
        "data": {
            "type": "testrecords",
            "id": full_test_record_id,
            "attributes": attributes_to_patch
        }
    }

    api_headers = get_polarion_api_headers(pat_token, content_type="application/json")
    response = None
    try:
        response = requests.patch(patch_url, headers=api_headers, json=payload, timeout=60, verify=VERIFY_SSL_REQUESTS)

        if response.status_code == 204:
            log_message("info", f"    Test Record '{full_test_record_id}' successfully patched for TC '{local_tc_id}' Iteration '{iteration_index_str}'.")
            return True
        else:
            log_message("error", f"    Failed to PATCH Test Record '{full_test_record_id}'. S:{response.status_code}, D:{response.text[:500]}")
            return False
    except Exception as e:
        log_message("error", f"    Exception patching Test Record '{full_test_record_id}': {e}")
        if response is not None: log_message("error", f"  Response text on exception: {response.text[:400]}")
        return False

def upload_attachment_to_test_record(
    project_id,
    full_test_run_id,
    test_case_project_id,
    local_tc_id,
    iteration_index_str,
    file_path,
    file_name_for_polarion,
    pat_token
):
    actual_tr_id = full_test_run_id.split('/')[-1]
    attachment_url_polarion = (
        f"{POLARION_BASE_URL}/projects/{project_id}/testruns/{actual_tr_id}"
        f"/testrecords/{test_case_project_id}/{local_tc_id}/{iteration_index_str}/attachments"
    )

    attachment_url = attachment_url_polarion

    log_message("info", f"    Uploading attachment '{file_name_for_polarion}' from '{file_path}' to Test Record for TC '{local_tc_id}', Iteration '{iteration_index_str}' of TR '{full_test_run_id}'")

    file_name_base = os.path.splitext(file_name_for_polarion)[0]
    attachment_lid = f"report_file_{file_name_base.replace('-', '_').replace('.', '_')}_{iteration_index_str}"
    title_attribute = file_name_for_polarion

    resource_meta = {
        "data": [{
            "type": "testrecord_attachments",
            "attributes": {
                "fileName": file_name_for_polarion,
                "title": title_attribute
            },
            "lid": attachment_lid,
        }]
    }

    headers_for_request = get_polarion_api_headers(pat_token, content_type=None)

    response = None
    try:
        if not os.path.exists(file_path):
            log_message("error", f"      Attachment file not found: {file_path}"); return False

        with open(file_path, 'rb') as f_content_binary:
            file_content_type = 'application/octet-stream'

            files_payload = {
                'resource': (None, json.dumps(resource_meta)),
                attachment_lid: (file_name_for_polarion, f_content_binary, file_content_type)
            }

            prepared_request = requests.Request('POST', attachment_url, headers=headers_for_request, files=files_payload).prepare()
            response = requests.post(attachment_url, headers=prepared_request.headers, data=prepared_request.body, timeout=120, verify=VERIFY_SSL_REQUESTS)

        if response.status_code == 201: 
            log_message("info", f"      Test Record Attachment '{file_name_for_polarion}' uploaded successfully."); return True
        elif response.status_code == 404:
            log_message("error", f"      Failed to upload Test Record attachment '{file_name_for_polarion}'. S:{response.status_code} - Not Found. Check IDs: P:{project_id}, TR:{actual_tr_id}, TCP:{test_case_project_id}, TC:{local_tc_id}, ITR:{iteration_index_str}. Details: {response.text[:500]}")
        else:
            log_message("error", f"      Failed to upload Test Record attachment '{file_name_for_polarion}'. S:{response.status_code}, D:{response.text[:500]}")
        return False
    except Exception as e:
        log_message("error", f"      Exception uploading Test Record attachment '{file_name_for_polarion}': {e}\n{traceback.format_exc(limit=2)}")
        if response is not None: log_message("error", f"  Response text on exception: {response.text[:400]}")
        return False
 
def get_executor_test_case_id(test_record_tc_id, project_id_of_tr, full_test_run_id, iteration_of_tr_to_update, pat_token):
    tr_short_id = full_test_run_id.split('/')[-1]
    
    api_url = (
        f"{POLARION_BASE_URL}/projects/{project_id_of_tr}/testruns/{tr_short_id}"
        f"/testrecords/{project_id_of_tr}/{test_record_tc_id}/{iteration_of_tr_to_update}"
        f"?include=testCase,testCase.backlinkedWorkItems,testCase.backlinkedWorkItems.workItem"
        f"&fields[testrecords]=testCase"
        f"&fields[workitems]=id,title,backlinkedWorkItems" 
        f"&fields[linkedworkitems]=@all" 
    )

    headers = get_polarion_api_headers(pat_token)
    response = None
    try:
        response = requests.get(api_url, headers=headers, timeout=60, verify=VERIFY_SSL_REQUESTS)
        response.raise_for_status()
        data = response.json()
        
        included_items = data.get("included", [])
        main_test_case_object_id = f"{project_id_of_tr}/{test_record_tc_id}"
        main_test_case_details = None
        for item in included_items:
            if item.get("type") == "workitems" and item.get("id") == main_test_case_object_id:
                main_test_case_details = item
                break
        
        if not main_test_case_details:
            log_message("error", f"        Could not find details for main Test Case '{main_test_case_object_id}' in included data for executor lookup.")
            return None 

        backlinks_data = main_test_case_details.get("relationships", {}).get("backlinkedWorkItems", {}).get("data", [])
        
        for backlink_ref in backlinks_data:
            backlink_id_full = backlink_ref.get("id") 
            if not backlink_id_full:
                continue

            parts = backlink_id_full.split('/')
            if len(parts) == 5:
                source_wi_local_id = parts[1]
                link_role = parts[2]
                
                if link_role == EXECUTOR_LINK_ROLE: 
                    log_message("info", f"        Found executor TC '{source_wi_local_id}' via backlink with role '{link_role}'.")
                    return source_wi_local_id
            else:
                log_message("warning", f"        Could not parse backlink ID structure: {backlink_id_full}")

        log_message("error", f"        No backlink with role '{EXECUTOR_LINK_ROLE}' found for TC '{test_record_tc_id}' (Iteration: {iteration_of_tr_to_update}). Cannot determine executor TC ID.")
        return None 

    except requests.exceptions.HTTPError as e_http:
        log_message("error", f"        HTTPError looking up executor TC for '{test_record_tc_id}' (Iteration: {iteration_of_tr_to_update}): {e_http.response.status_code} - {e_http.response.text[:200]}")
    except Exception as e:
        log_message("error", f"        Exception looking up executor TC for '{test_record_tc_id}' (Iteration: {iteration_of_tr_to_update}): {e}\n{traceback.format_exc(limit=1)}")
    
    return None

def process_test_run_found_by_poller(project_id, full_test_run_id, pat_token, is_last_test_run):
    log_message("info", f"--- Start Processing TR: {full_test_run_id} (Project: {project_id}) ---")
    waiting_record_details_list = fetch_test_cases_from_polarion_test_run(project_id, full_test_run_id, pat_token)
    
    if not waiting_record_details_list:
        log_message("info", f"No 'waiting' Test Records found for TR '{full_test_run_id}'.")
        return
        
    log_message("info", f"Starting execution for {len(waiting_record_details_list)} Test Record(s) (TC/iteration pair(s)) in 'waiting' state for TR '{full_test_run_id}'.")
    any_tc_processed_successfully_in_this_run = False
    all_valid_tc_attempts_were_successful = True 

    num_waiting_records = len(waiting_record_details_list)
    for i, record_detail in enumerate(waiting_record_details_list):
        is_last_record_in_run = (i == num_waiting_records - 1)
        tc_id_to_update = record_detail["tc_id"]        
        iteration_str_to_update = record_detail["iteration"]

        log_message("info", f"  -- Processing Test Record for TC: {tc_id_to_update} (Iteration: {iteration_str_to_update}) in TR {full_test_run_id} --")
        current_record_processing_fully_successful = False

        executor_tc_id = get_executor_test_case_id(tc_id_to_update, project_id, full_test_run_id, iteration_str_to_update, pat_token)
        
        if not executor_tc_id:
            log_message("error", f"    CRITICAL: Cannot determine executor TC ID for Test Record '{tc_id_to_update}' (Iteration: {iteration_str_to_update}). Skipping processing for this Test Record.")
            all_valid_tc_attempts_were_successful = False 
            log_message("info", f"  -- End Processing Test Record for TC: {tc_id_to_update} (Iteration: {iteration_str_to_update}, Skipped due to missing executor ID) --");
            continue 

        config_file_path = os.path.join(CONFIG_DIR_PATH, CONFIG_JSON_FILENAME)
        config_updated_successfully = False
        try:
            if not os.path.exists(config_file_path):
                log_message("error", f"    Configuration file '{config_file_path}' not found. Cannot update TestName for executor TC {executor_tc_id}.")
                all_valid_tc_attempts_were_successful = False
                log_message("info", f"  -- End Processing Test Record for TC: {tc_id_to_update} (Iteration: {iteration_str_to_update}, Skipped due to missing config file) --");
                continue
            
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            
            config_data["TestName"] = executor_tc_id
            
            if (ALWAYS_CLOSE_WIN_SAM) or (is_last_test_run and is_last_record_in_run):
                config_data["CloseWinSam"] = True
            else:
                config_data["CloseWinSam"] = False
            
            with open(config_file_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            log_message("info", f"    Updated config '{config_file_path}': TestName='{executor_tc_id}', CloseWinSam={config_data['CloseWinSam']}.")
            config_updated_successfully = True

        except Exception as e_cfg:
             log_message("error", f"    Error with configuration file '{config_file_path}': {e_cfg}. Cannot update TestName for executor TC {executor_tc_id}.")

        if not config_updated_successfully:
            all_valid_tc_attempts_were_successful = False
            log_message("error", f"    Skipping execution of TestRunner.py for executor TC {executor_tc_id} due to config update failure.")
            log_message("info", f"  -- End Processing Test Record for TC: {tc_id_to_update} (Iteration: {iteration_str_to_update}, Skipped due to config update failure) --");
            continue
        
        log_message("info", f"    Executing TestRunner.py (config updated for executor: {executor_tc_id})")
        
        report_html_name = f"{executor_tc_id}.html"
        report_html_path = os.path.join(REPORT_DIR_PATH, report_html_name)
        report_html_full_name = f"{executor_tc_id}_Full.html"
        report_html_full_path = os.path.join(REPORT_DIR_PATH, report_html_full_name)

        if os.path.exists(report_html_path):
            os.remove(report_html_path)

        if os.path.exists(report_html_full_path):
            os.remove(report_html_full_path)

        start_test_time = start_test_timer()

        exit_code_testrunner, _, _ = run_local_testrunner_script(
            TESTRUNNER_SCRIPT_NAME,
            POLLER_SCRIPT_DIR
        )

        time.sleep(5)

        test_time = get_test_duration(start_test_time)
        
        log_message("error", f"   {test_time}'")

        if exit_code_testrunner > 1 and exit_code_testrunner != 0:
            log_message("error", f"    TestRunner.py execution terminated with code {exit_code_testrunner} for executor TC {executor_tc_id}.")
        elif exit_code_testrunner == 1:
            log_message("warning", f"    TestRunner.py (TestStand) likely completed with test failures (exit code 1) for executor TC {executor_tc_id}. Processing reports.")
        
        if not os.path.exists(report_html_path):
            log_message("error", f"    HTML report '{report_html_path}' (expected for executor TC {executor_tc_id}) NOT found after TestStand execution! Cannot update Test Record for {tc_id_to_update} (Iteration: {iteration_str_to_update}).")
            all_valid_tc_attempts_were_successful = False
        else:
            log_message("info", f"    HTML report '{report_html_path}' found for executor TC {executor_tc_id}.")
            extracted_results = extract_test_results_from_html_report(report_html_path, test_time)

            if extracted_results["outcome"] == "null":
                current_record_processing_fully_successful = False

            unlocked_for_patch = False
            try:
                if set_polarion_test_run_status(project_id, full_test_run_id, STATUS_TR_UNLOCKED, pat_token):
                    unlocked_for_patch = True
                    if patch_polarion_test_record(
                        project_id, 
                        full_test_run_id,
                        project_id, 
                        tc_id_to_update,
                        iteration_str_to_update,
                        extracted_results,
                        pat_token
                    ):
                        log_message("info", f"      Test Record for TC '{tc_id_to_update}' (Iteration: {iteration_str_to_update}) successfully patched with results.")
                        current_record_processing_fully_successful = True
                        any_tc_processed_successfully_in_this_run = True
                    else:
                        log_message("error", f"      Failed to PATCH Test Record for TC '{tc_id_to_update}' (Iteration: {iteration_str_to_update}) with results from HTML report '{report_html_name}'.")
                        all_valid_tc_attempts_were_successful = False
                else:
                    log_message("error", f"      Failed to temporarily unlock TR '{full_test_run_id}' for PATCH. Skipping PATCH.")
                    all_valid_tc_attempts_were_successful = False
            finally:
                if unlocked_for_patch:
                    if not set_polarion_test_run_status(project_id, full_test_run_id, STATUS_TR_LOCKED, pat_token):
                        log_message("critical", f"      CRITICAL: Failed to re-lock TR '{full_test_run_id}' after PATCH attempt! State might be inconsistent.")
        
        html_files_to_upload_to_record = []
        if os.path.exists(report_html_path):
            html_files_to_upload_to_record.append((report_html_name, report_html_path))
        if os.path.exists(report_html_full_path):
            log_message("info", f"    Full HTML report '{report_html_full_path}' found for executor TC {executor_tc_id}.")
            html_files_to_upload_to_record.append((report_html_full_name, report_html_full_path))

        if current_record_processing_fully_successful and html_files_to_upload_to_record:
            log_message("info", f"    Attempting to update attachments for TC {tc_id_to_update} (Iteration: {iteration_str_to_update})...")
            all_attachments_successful_for_this_tc = True
            unlocked_for_attachment_ops = False
            try:
                if set_polarion_test_run_status(project_id, full_test_run_id, STATUS_TR_UNLOCKED, pat_token):
                    unlocked_for_attachment_ops = True

                    existing_attachments = get_existing_attachments_for_test_record(
                        project_id, full_test_run_id, project_id, tc_id_to_update, iteration_str_to_update, pat_token
                    )
                    if existing_attachments:
                        if not delete_attachments_from_test_record(
                            project_id, full_test_run_id, project_id, tc_id_to_update, iteration_str_to_update, existing_attachments, pat_token
                        ):
                            log_message("warning", "      Could not delete all previous attachments. Proceeding with upload anyway.")
                            all_attachments_successful_for_this_tc = False
                            all_valid_tc_attempts_were_successful = False

                    if all_attachments_successful_for_this_tc:
                        log_message("info", f"    Uploading {len(html_files_to_upload_to_record)} new attachments...")
                        for name, path_to_file in html_files_to_upload_to_record:
                            if not upload_attachment_to_test_record(
                                project_id,
                                full_test_run_id,
                                project_id,
                                tc_id_to_update,
                                iteration_str_to_update,
                                path_to_file,
                                name,
                                pat_token
                            ):
                                log_message("error", f"      Upload failed for new attachment '{name}'.")
                                all_attachments_successful_for_this_tc = False
                                all_valid_tc_attempts_were_successful = False
                else:
                    log_message("error", f"      Failed to temporarily unlock TR '{full_test_run_id}' for attachment operations. Skipping all attachment updates.")
                    all_attachments_successful_for_this_tc = False
                    all_valid_tc_attempts_were_successful = False
            finally:
                if unlocked_for_attachment_ops:
                    if not set_polarion_test_run_status(project_id, full_test_run_id, STATUS_TR_LOCKED, pat_token):
                        log_message("critical", f"      CRITICAL: Failed to re-lock TR '{full_test_run_id}' after attachment operations! State might be inconsistent.")

            if not all_attachments_successful_for_this_tc:
                current_record_processing_fully_successful = False
        elif not current_record_processing_fully_successful and html_files_to_upload_to_record:
            log_message("warning", f"    Skipping HTML attachment upload for TC {tc_id_to_update} (Iteration: {iteration_str_to_update}) because result patching failed.")
            
        if not current_record_processing_fully_successful:
            all_valid_tc_attempts_were_successful = False 
            log_message("error", f"    Processing for Test Record of TC {tc_id_to_update} (Iteration: {iteration_str_to_update}) was not fully successful.")
        
        log_message("info", f"  -- End Processing Test Record for TC: {tc_id_to_update} (Iteration: {iteration_str_to_update}) --"); time.sleep(1)
        
    if not waiting_record_details_list: 
        final_tr_status_message = "NO_WAITING_TEST_RECORDS_FOUND"
    elif all_valid_tc_attempts_were_successful and any_tc_processed_successfully_in_this_run:
        final_tr_status_message = "ALL_VALID_TEST_RECORDS_PROCESSED_SUCCESSFULLY"
    elif any_tc_processed_successfully_in_this_run:
        final_tr_status_message = "PARTIAL_SUCCESS_SOME_TEST_RECORDS_SKIPPED_OR_ERRORED"
    else: 
        final_tr_status_message = "NO_TEST_RECORDS_SUCCESSFULLY_PROCESSED_OR_ALL_SKIPPED_FAILED"

    log_message("info", f"--- End Processing TR: {full_test_run_id}. Overall TR processing result for this iteration: {final_tr_status_message} ---")

def poller_main(current_project_id, current_pat_token, specific_test_run_short_id=None):
    log_message("info", "Starting Polarion Poller...")
    if VERIFY_SSL_REQUESTS is False: log_message("warning", "SSL CERTIFICATE VERIFICATION IS DISABLED.")
    
    while True: 
        test_runs_to_process_full_ids = []

        if specific_test_run_short_id:
            candidate_full_tr_id = None
            if '/' in specific_test_run_short_id:
                if not specific_test_run_short_id.startswith(current_project_id + '/'):
                    log_message("error", f"Specific Test Run ID '{specific_test_run_short_id}' (full form) does not belong to the specified project '{current_project_id}'. Skipping.")
                else:
                    candidate_full_tr_id = specific_test_run_short_id
            else:
                candidate_full_tr_id = f"{current_project_id}/{specific_test_run_short_id}"
            
            if candidate_full_tr_id:
                log_message("info", f"Specific Test Run ID provided. Targeting: '{candidate_full_tr_id}'. Verifying status...")
                tr_details = get_polarion_test_run_details(current_project_id, candidate_full_tr_id, current_pat_token)
                if tr_details:
                    current_status = tr_details.get("attributes", {}).get("status")
                    if current_status == STATUS_TR_UNLOCKED:
                        log_message("info", f"Specified Test Run '{candidate_full_tr_id}' is in '{STATUS_TR_UNLOCKED}' state. Proceeding.")
                        test_runs_to_process_full_ids = [candidate_full_tr_id]
                    else:
                        log_message("warning", f"Specified Test Run '{candidate_full_tr_id}' is in status '{current_status}', not '{STATUS_TR_UNLOCKED}'. Skipping.")
                else:
                    log_message("error", f"Could not retrieve details for specified Test Run '{candidate_full_tr_id}' or it does not exist. Skipping.")
            
            if not test_runs_to_process_full_ids:
                log_message("info", "No specific Test Run will be processed due to status check or retrieval failure.")
        else:
            log_message("info", "New polling cycle for open Test Runs...")
            test_runs_to_process_full_ids = find_test_runs_to_process(current_project_id, current_pat_token)

        if not test_runs_to_process_full_ids:
            log_message("info", f"No Test Runs in status '{STATUS_TR_UNLOCKED}' to process. Pausing for {POLLING_INTERVAL_SECONDS}s.")
        
        num_test_runs_found = len(test_runs_to_process_full_ids)
        for i, full_tr_id in enumerate(test_runs_to_process_full_ids):
            is_last_run = (i == num_test_runs_found - 1)
            log_message("info", f"Attempting to process TR: {full_tr_id}")
            
            log_message("info", f"Attempting to lock TR '{full_tr_id}' by setting status to '{STATUS_TR_LOCKED}'.")
            locked_successfully = set_polarion_test_run_status(
                current_project_id, full_tr_id, STATUS_TR_LOCKED, current_pat_token
            )

            if locked_successfully:
                try:
                    process_test_run_found_by_poller(
                        current_project_id,
                        full_tr_id,
                        current_pat_token,
                        is_last_run
                    )
                finally:
                    log_message("info", f"Attempting to unlock TR '{full_tr_id}' by setting status to '{STATUS_TR_UNLOCKED}'.")
                    unlocked_successfully = set_polarion_test_run_status(
                        current_project_id, full_tr_id, STATUS_TR_UNLOCKED, current_pat_token
                    )
                    if not unlocked_successfully:
                        log_message("critical", f"CRITICAL: Failed to unlock TR '{full_tr_id}' (set back to '{STATUS_TR_UNLOCKED}')! Manual intervention may be required.")
            else:
                log_message("warning", f"Failed to lock TR '{full_tr_id}' (set to '{STATUS_TR_LOCKED}'). Skipping this Test Run for this cycle.")
            
            log_message("info", f"TR '{full_tr_id}' processing attempt cycle finished. Manual verification needed by user.")

        if not LOOP_MODE:
            log_message("info", "Exiting poller. Loop Mode Off")
            break 
 
        time.sleep(POLLING_INTERVAL_SECONDS)
      
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polarion Poller for automated test execution.")
    parser.add_argument("--project-id", required=True, help="Polarion Project ID (e.g., BJEQPTraining)")
    parser.add_argument("--pat", required=True, help="Polarion Personal Access Token")
    parser.add_argument("--test-run-id", required=False, default=None, 
                        help="Specific Test Run ID (short ID, e.g., 2025-06-05T10-29-22-IT_TESTSTAND_POLARION_3) to process. If provided, only this Test Run will be processed, and the poller will exit after.")
    args = parser.parse_args()
    cli_project_id = args.project_id
    cli_pat = args.pat
    cli_specific_test_run_id = args.test_run_id

    if not cli_pat or len(cli_pat) < 100:
        log_message("critical", "FATAL ERROR: Polarion Personal Access Token (PAT) missing or too short!"); sys.exit(1)
    
    os.makedirs(REPORT_DIR_PATH, exist_ok=True)
    os.makedirs(CONFIG_DIR_PATH, exist_ok=True)
    initial_config_file_path = os.path.join(CONFIG_DIR_PATH, CONFIG_JSON_FILENAME)
    if not os.path.exists(initial_config_file_path):
        log_message("warning", f"Configuration file '{initial_config_file_path}' not found. Creating a default one with an empty 'TestName'.")
        try:
            with open(initial_config_file_path, 'w') as f_cfg:
                json.dump({"TestName": None, "OtherConfig": "DefaultValue"}, f_cfg, indent=4)
        except IOError as e_io_cfg:
            log_message("critical", f"FATAL ERROR: Could not create default configuration file '{initial_config_file_path}': {e_io_cfg}"); sys.exit(1)
            
    poller_main(cli_project_id, cli_pat, cli_specific_test_run_id)