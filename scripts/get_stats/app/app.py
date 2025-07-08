import requests
import json
import argparse
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

from matrics_answer import main


class LogReceiver:
    def __init__(self):
        self.sender_url = "http://localhost:8003/logs"
        self.save_dir = Path("logs")
        self.log_prefix = "log_"
        self.date_format = "%Y%m%d"

        self.save_dir.mkdir(parents=True, exist_ok=True)

    def fetch_and_save_log(self) -> dict:
        """
        Fetches logs from remote service and saves them locally with timestamp.
        Also deletes logs older than N days.
        """
        try:
            response = requests.get(self.sender_url, timeout=10)
            response.raise_for_status()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.log_prefix}{timestamp}.json"
            save_path = self.save_dir / filename

            self.clean_old_logs(max_days_old=30)

            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(response.json(), f, ensure_ascii=False, indent=2)

            return {"status": "success", "filename": filename}

        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Connection error: {str(e)}"}
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON received"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def clean_old_logs(self, max_days_old: int = 30) -> list:
        """
        Deletes log files older than max_days_old based on filename timestamps.
        """
        cutoff_date = datetime.now() - timedelta(days=max_days_old)
        deleted_files = []

        for log_file in self.save_dir.glob(f"{self.log_prefix}*.json"):
            try:
                date_str = log_file.stem[len(self.log_prefix):].split("_")[0]
                file_date = datetime.strptime(date_str, self.date_format)
                if file_date < cutoff_date:
                    os.remove(log_file)
                    deleted_files.append(log_file.name)
            except (ValueError, IndexError):
                continue
            except Exception as e:
                print(f"Error deleting {log_file.name}: {e}")

        return deleted_files


if __name__ == "__main__":
    receiver = LogReceiver()
    result = receiver.fetch_and_save_log()
    print(result)

    if result["status"] == "error":
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--flag_last", action="store_true", help="Enable flag for latest processing")
    args = parser.parse_args()

    main(args.flag_last)
