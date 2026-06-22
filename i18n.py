import json
import os
from flask import session


class I18n:
    def __init__(self):
        self.translations = {}
        self.default_lang = 'en'

    def init_app(self, app):
        lang_dir = os.path.join(app.root_path, 'translations')
        for f in os.listdir(lang_dir):
            if f.endswith('.json'):
                lang = f.replace('.json', '')
                with open(os.path.join(lang_dir, f), 'r', encoding='utf-8') as fp:
                    self.translations[lang] = json.load(fp)

        @app.context_processor
        def inject_i18n():
            lang = session.get('lang', self.default_lang)
            trans = self.translations.get(lang, self.translations.get(self.default_lang, {}))

            def _(key, **kwargs):
                text = trans.get(key, key)
                if kwargs:
                    text = text.format(**kwargs)
                return text

            def t(key, **kwargs):
                text = trans.get(key, key)
                if kwargs:
                    text = text.format(**kwargs)
                return text

            return dict(_=_, t=t, current_lang=lang)

    def translate(self, key, **kwargs):
        from flask import current_app
        with current_app.app_context():
            lang = session.get('lang', self.default_lang)
        trans = self.translations.get(lang, self.translations.get(self.default_lang, {}))
        text = trans.get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def get_js_translations(self):
        lang = session.get('lang', self.default_lang)
        trans = self.translations.get(lang, self.translations.get(self.default_lang, {}))
        en_trans = self.translations.get('en', {})
        js_keys = [
            'no_results', 'no_title', 'network_error', 'processing', 'save',
            'saved', 'no_loaded_entry', 'molecular_weight', 'isoelectric_point',
            'aromaticity', 'instability_index', 'legend_green', 'legend_favorable',
            'legend_pink', 'legend_unfavorable', 'legend_lower_better',
            'identical', 'improved', 'worsened', '3d_canvas_not_found',
            '3d_not_loaded', 'error_prefix', 'length_da', 'weight_da',
            'iso_point', 'aromaticity_pct', 'stability', 'metric',
            'difference_delta', 'save_notes_button', 'run_mutation_button',
            'original_label', 'mutant_label', 'selected_count',
            'notes_status_network_error', 'pdb_badge'
        ]
        result = {}
        for k in js_keys:
            result[k] = trans.get(k, en_trans.get(k, k))
        return result


i18n = I18n()
