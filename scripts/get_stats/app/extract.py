import json
import glob
import os
import re
from datetime import datetime
from collections import defaultdict
from pathlib import Path


def extract_datetime(filename: str) -> datetime:
    """Extract timestamp from a filename."""
    parts = os.path.basename(filename).split('_')
    datetime_str = parts[1] + "_" + parts[2].split('.')[0]
    return datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")


def extract_nested_values(data, parent_key: str = '', separator: str = '.') -> dict:
    """Flatten nested dicts/lists with compound keys."""
    result = defaultdict(list)

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                nested = extract_nested_values(value, new_key, separator)
                for k, v in nested.items():
                    result[k].extend(v)
            else:
                if parent_key:
                    result[new_key].append(value)

    elif isinstance(data, list):
        for item in data:
            nested = extract_nested_values(item, parent_key, separator)
            for k, v in nested.items():
                result[k].extend(v)

    return result


def extract_specific_values(data, target_keys=None) -> dict:
    """Extract specific question/answer fields from nested structure."""
    if target_keys is None:
        target_keys = ['texts.question.text', 'texts.answer.text']

    result = defaultdict(list)

    def _extract(obj, current_key=''):
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{current_key}.{key}" if current_key else key
                if new_key in target_keys:
                    result[new_key].append(str(value) if isinstance(value, (dict, list)) else value)
                else:
                    _extract(value, new_key)

        elif isinstance(obj, list):
            for item in obj:
                _extract(item, current_key)

    _extract(data)
    return result


def is_ip_address(text: str) -> bool:
    """Check if a string is a valid IPv4 address."""
    ip_regex = (
        r'^(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}'
        r'(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)$'
    )
    return bool(re.fullmatch(ip_regex, text))


def filter_data_keep_ips(data):
    """Recursively remove all string values except valid IPs."""
    if isinstance(data, dict):
        return {
            key: filter_data_keep_ips(value)
            for key, value in data.items()
            if not (isinstance(value, str) and not is_ip_address(value))
        }

    elif isinstance(data, list):
        return [
            filter_data_keep_ips(item)
            for item in data
            if not (isinstance(item, str) and not is_ip_address(item))
        ]

    else:
        return data


def separate_ips_from_data(data) -> dict:
    """Extract all IP addresses and separate them from the rest of the data."""
    ips = []

    def recursive_scan(obj):
        if isinstance(obj, dict):
            cleaned = {}
            for key, value in obj.items():
                if isinstance(value, str) and is_ip_address(value):
                    ips.append(value)
                elif isinstance(value, (dict, list)):
                    cleaned[key] = recursive_scan(value)
                else:
                    cleaned[key] = value
            return cleaned

        elif isinstance(obj, list):
            cleaned = []
            for item in obj:
                if isinstance(item, str) and is_ip_address(item):
                    ips.append(item)
                elif isinstance(item, (dict, list)):
                    cleaned.append(recursive_scan(item))
                else:
                    cleaned.append(item)
            return cleaned

        return obj

    return {
        "ip": list(ips),
        "data": recursive_scan(data)
    }


def process_all_logs(logs_dir: str = "logs", flag_last: bool = False):
    """Load and process log files, optionally only the latest one."""
    log_files = glob.glob(f"{logs_dir}/*.json")
    if not log_files:
        print(f"No JSON logs found in: {logs_dir}")
        return {"stats": {}, "metrics": {}}

    if flag_last:
        log_files = [max(log_files, key=extract_datetime)]

    combined_data = []
    date_str = "all"

    for log_file in log_files:
        try:
            if flag_last:
                base = Path(log_file).stem[len("log_"):]
                parts = base.split("_")
                date_str = f"{parts[0]}_{parts[1]}"
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                combined_data.append(data)
        except json.JSONDecodeError:
            print(f"Invalid JSON in file: {log_file}")
        except Exception as e:
            print(f"Error reading {log_file}: {str(e)}")

    flattened = extract_nested_values(combined_data)
    cleaned = filter_data_keep_ips(flattened)
    final = separate_ips_from_data(cleaned)
    extracted_fields = extract_specific_values(combined_data)

    return final, extracted_fields, date_str


if __name__ == "__main__":
    process_all_logs()
