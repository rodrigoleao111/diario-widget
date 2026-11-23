import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from . import config
from .db import tickets_em


def coletar(con, desde):
    saida = subprocess.run(
        [config.SVN_EXE, "log", "--search", config.SVN_USER, "-r", f"{{{desde.isoformat()}}}:HEAD",
         "--xml", config.SVN_URL],
        capture_output=True, text=True, encoding="utf-8", timeout=600, check=True,
    ).stdout
    novos = 0
    for e in ET.fromstring(saida).findall("logentry"):
        if e.findtext("author") != config.SVN_USER:
            continue
        rev, msg = e.get("revision"), (e.findtext("msg") or "").strip()
        t = datetime.fromisoformat(e.findtext("date").replace("Z", "+00:00")).astimezone().replace(tzinfo=None)
        cur = con.execute(
            "INSERT OR IGNORE INTO eventos(ref, ts, data, origem, projeto, categoria, tickets, texto)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (f"svn:{rev}", t.isoformat(" ", "seconds"), t.date().isoformat(), "svn", "SVN", "trabalho",
             tickets_em(msg), f"r{rev} — {msg}"),
        )
        novos += cur.rowcount
    con.commit()
    return novos
