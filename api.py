import json
import os
import string
import itertools
import urllib.request
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, request, jsonify, session
from db import get_db, get_user_id, get_versions
from bio_engine import run_analysis
from config import Config
from i18n import i18n

api_bp = Blueprint('api', __name__)

PDB_CACHE_FILE = Config.PDB_CACHE_FILE

_pdb_cache_ids = set()
_pdb_cache_titles = {}
_pdb_cache_lock = threading.Lock()


def _load_pdb_cache():
    global _pdb_cache_ids, _pdb_cache_titles
    if os.path.exists(PDB_CACHE_FILE):
        try:
            with open(PDB_CACHE_FILE) as f:
                data = json.load(f)
                _pdb_cache_ids = set(data.get("ids", []))
                _pdb_cache_titles = data.get("titles", {})
        except Exception:
            _pdb_cache_ids = set()
            _pdb_cache_titles = {}


def _save_pdb_cache():
    with open(PDB_CACHE_FILE, 'w') as f:
        json.dump({
            "ids": list(_pdb_cache_ids),
            "titles": _pdb_cache_titles
        }, f)


def _fetch_missing_by_prefix(prefix):
    prefix_upper = prefix.upper()
    alphabet = string.digits + string.ascii_uppercase
    remaining = 4 - len(prefix)
    all_possible = [prefix_upper + ''.join(combo) for combo in itertools.product(alphabet, repeat=remaining)]

    new_ids = []
    batch_size = 500

    def check_batch(batch):
        local_found = []
        query = {
            "query": {
                "type": "terminal",
                "service": "text",
                "parameters": {
                    "attribute": "rcsb_id",
                    "operator": "in",
                    "value": batch
                }
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": 500}
            }
        }
        req = urllib.request.Request(
            'https://search.rcsb.org/rcsbsearch/v2/query',
            data=json.dumps(query).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            local_found = [x['identifier'] for x in data.get('result_set', [])]
        except Exception:
            pass
        return local_found

    batches = [all_possible[i:i+batch_size] for i in range(0, len(all_possible), batch_size)]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_batch, batch): batch for batch in batches}
        for future in as_completed(futures):
            try:
                found = future.result()
                new_ids.extend(found)
            except Exception:
                pass

    return new_ids


def _fetch_titles(pdb_ids):
    if not pdb_ids:
        return {}
    entries_query = ' '.join(
        f'e{i}: entry(entry_id:"{pid}"){{rcsb_id struct{{title}}}}'
        for i, pid in enumerate(pdb_ids)
    )
    payload = json.dumps({"query": "{" + entries_query + "}"})
    req = urllib.request.Request(
        'https://data.rcsb.org/graphql',
        data=payload.encode(),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    titles = {}
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        for key, val in data.get('data', {}).items():
            if val:
                titles[val.get('rcsb_id', '')] = val.get('struct', {}).get('title', '')
    except Exception:
        pass
    return titles


_load_pdb_cache()


@api_bp.route("/autocomplete")
def autocomplete():
    q = request.args.get("q", "").strip().lower()
    limit = min(int(request.args.get("limit", 10)), 20)
    if len(q) < 2:
        return jsonify([])

    prefix_upper = q.upper()
    with _pdb_cache_lock:
        matching = sorted([pid for pid in _pdb_cache_ids if pid.startswith(prefix_upper)])

    if len(matching) < limit:
        try:
            new_ids = _fetch_missing_by_prefix(q)
            with _pdb_cache_lock:
                for pid in new_ids:
                    _pdb_cache_ids.add(pid)
                new_matching = sorted([pid for pid in _pdb_cache_ids if pid.startswith(prefix_upper)])
            if len(new_matching) > len(matching):
                matching = new_matching
                _save_pdb_cache()
        except Exception:
            pass

    matching = matching[:limit]

    need_titles = [pid for pid in matching if pid not in _pdb_cache_titles]
    if need_titles:
        titles = _fetch_titles(need_titles)
        with _pdb_cache_lock:
            _pdb_cache_titles.update(titles)
            _save_pdb_cache()

    results = []
    with _pdb_cache_lock:
        for pid in matching:
            results.append({
                "id": pid,
                "title": _pdb_cache_titles.get(pid, "")
            })
    return jsonify(results)


@api_bp.route("/save_notes", methods=["POST"])
def save_notes():
    if not get_user_id():
        return jsonify({"error": i18n.translate("not_logged_in")}), 401
    entry_id = request.form.get("entry_id", "")
    notes = request.form.get("notes", "")
    if not entry_id:
        return jsonify({"error": i18n.translate("missing_id")}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE protein_history SET notes = ? WHERE id = ? AND user_id = ?',
                  (notes, entry_id, get_user_id()))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/versions", methods=["POST"])
def versions():
    if not get_user_id():
        return jsonify({"error": i18n.translate("not_logged_in")}), 401
    vg = request.form.get("version_group", "")
    if not vg:
        return jsonify({"error": i18n.translate("missing_version_group")}), 400
    data = get_versions(get_user_id(), vg)
    entries = []
    for row in data:
        entries.append({
            "id": row[0],
            "pdb_id": row[1].upper() if row[1] else i18n.translate("na"),
            "length": row[2],
            "weight": row[3],
            "stability": row[4],
            "timestamp": row[5],
            "version_num": row[6]
        })
    return jsonify({"versions": entries})


@api_bp.route("/mutate", methods=["POST"])
def mutate():
    if not get_user_id():
        return jsonify({"error": i18n.translate("not_logged_in")}), 401
    seq = request.form.get("sequence", "")
    position_str = request.form.get("position", "")
    new_aa = request.form.get("new_aa", "").upper().strip()

    if not seq or not position_str or not new_aa:
        return jsonify({"error": i18n.translate("missing_parameters")}), 400

    try:
        position = int(position_str)
    except ValueError:
        return jsonify({"error": i18n.translate("invalid_position")}), 400

    standard_aa = set("ACDEFGHIKLMNPQRSTVWY")
    clean_seq = "".join(c for c in seq.upper() if c in standard_aa)

    if not clean_seq:
        return jsonify({"error": i18n.translate("invalid_sequence_chars")}), 400
    if position < 1 or position > len(clean_seq):
        return jsonify({"error": i18n.translate("position_out_of_range", length=len(clean_seq))}), 400
    if new_aa not in standard_aa:
        return jsonify({"error": i18n.translate("invalid_aa", aa=new_aa)}), 400

    original_aa = clean_seq[position - 1]
    mutated = clean_seq[:position - 1] + new_aa + clean_seq[position:]

    original_results = run_analysis(clean_seq)
    mutant_results = run_analysis(mutated)

    if "error" in original_results:
        return jsonify({"error": original_results["error"]}), 400
    if "error" in mutant_results:
        return jsonify({"error": mutant_results["error"]}), 400

    return jsonify({
        "original": original_results,
        "mutant": mutant_results,
        "position": position,
        "original_aa": original_aa,
        "mutant_aa": new_aa
    })


@api_bp.route("/compare", methods=["POST"])
def compare():
    if not get_user_id():
        return jsonify({"error": i18n.translate("not_logged_in")}), 401
    entry_ids = request.form.get("entry_ids", "")
    if not entry_ids:
        return jsonify({"error": i18n.translate("missing_ids")}), 400
    ids = [int(x.strip()) for x in entry_ids.split(",") if x.strip()]
    if len(ids) < 2:
        return jsonify({"error": i18n.translate("select_at_least_2")}), 400

    conn = get_db()
    c = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    c.execute(f'SELECT id, pdb_id, sequence, timestamp FROM protein_history WHERE id IN ({placeholders}) AND user_id = ?', ids + [get_user_id()])
    rows = c.fetchall()
    conn.close()

    if len(rows) < 2:
        return jsonify({"error": i18n.translate("no_valid_entries")}), 400

    entries = []
    for row in rows:
        entry_id, pdb_id, seq, ts = row
        analysis = run_analysis(seq, pdb_id=pdb_id or "")
        if "error" not in analysis:
            analysis['entry_id'] = entry_id
            analysis['pdb_id'] = pdb_id.upper() if pdb_id else i18n.translate("na")
            analysis['timestamp'] = ts
            entries.append(analysis)

    return jsonify({"entries": entries})
