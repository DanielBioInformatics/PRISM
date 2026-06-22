from Bio.SeqUtils.ProtParam import ProteinAnalysis
from cache import cached_analysis


@cached_analysis()
def run_analysis(sequence, pdb_id=""):
    standard_aa = set("ACDEFGHIKLMNPQRSTVWY")
    clean_seq = "".join(c for c in sequence.upper() if c in standard_aa)
    if len(clean_seq) < 2:
        return {"error": "sequence_too_short"}

    if not clean_seq:
        return {"error": "invalid_seq_chars"}

    try:
        analysis = ProteinAnalysis(clean_seq)

        weight = analysis.molecular_weight()
        pi = analysis.isoelectric_point()
        gravy = analysis.gravy()
        aromaticity = analysis.aromaticity()
        instability = analysis.instability_index()

        helix, turn, sheet = analysis.secondary_structure_fraction()

        ext_reduced, ext_oxidized = analysis.molar_extinction_coefficient()

        if gravy > 0.3:
            strategy_key = "bio_strategy_hydrophobic"
        elif -0.3 <= gravy <= 0.3:
            strategy_key = "bio_strategy_amphipathic"
        else:
            strategy_key = "bio_strategy_hydrophilic"

        if pi < 6.0:
            charge_key = "bio_charge_acidic"
        elif 6.0 <= pi <= 8.0:
            charge_key = "bio_charge_neutral"
        else:
            charge_key = "bio_charge_basic"

        if instability < 40:
            stability_status = "STABIL"
            is_stable = True
            stability_key = "bio_stability_stable"
        else:
            stability_status = "INSTABIL"
            is_stable = False
            stability_key = "bio_stability_unstable"

        aa_pct = analysis.amino_acids_percent
        aa_groups = {
            "aa_group_hydrophobic": [('A','Ala'),('V','Val'),('I','Ile'),('L','Leu'),('M','Met'),('F','Phe'),('Y','Tyr'),('W','Trp')],
            "aa_group_positive": [('K','Lys'),('R','Arg'),('H','His')],
            "aa_group_negative": [('D','Asp'),('E','Glu')],
            "aa_group_polar": [('S','Ser'),('T','Thr'),('N','Asn'),('Q','Gln')],
            "aa_group_special": [('G','Gly'),('P','Pro'),('C','Cys')]
        }

        formatted_groups = {}
        for g_name, aa_list in aa_groups.items():
            formatted_groups[g_name] = []
            for c1, c3 in aa_list:
                pct = round(aa_pct.get(c1, 0), 2)
                formatted_groups[g_name].append({"c1": c1, "c3": c3, "pct": pct})

        return {
            "length": len(clean_seq),
            "weight": round(weight, 2),
            "pi": round(pi, 2),
            "gravy": round(gravy, 2),
            "aromaticity": round(aromaticity * 100, 2),
            "instability": round(instability, 2),
            "stability_status": stability_status,
            "is_stable": is_stable,
            "stability_key": stability_key,
            "stability_info_key": stability_key,
            "helix": round(helix * 100, 2),
            "turn": round(turn * 100, 2),
            "sheet": round(sheet * 100, 2),
            "ext_reduced": ext_reduced,
            "ext_oxidized": ext_oxidized,
            "strategy": strategy_key,
            "charge_info": charge_key,
            "aa_groups": formatted_groups
        }
    except Exception as e:
        return {"error": str(e)}
