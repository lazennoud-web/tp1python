import re

# 4 groupes : mois, jour, heure (hh:mm:ss), message
PATTERN = re.compile(r'(\w{3})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})\s+\S+\s+\S+:\s(.*)')
IP_PATTERN = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')

def extract_from_row(row):
    match = PATTERN.search(row)
    if not match:
        return None
    month, day, time, message = match.groups()
    ip = IP_PATTERN.search(message)
    return {
        "month": month,
        "day": int(day),
        "time": time,
        "message": message.strip(),
        "ip": ip.group(1) if ip else None,
    }

if __name__ == "__main__":
    from ingestion import raw
    print(extract_from_row(raw.toRows('./data')[0]))