"""
Translations for the College Match app.

Usage:
    from src.i18n import t, get_lang
    lang = get_lang()          # reads st.session_state["lang"], default "EN"
    heading = t("apply_heading", lang)

Every key must have both "EN" and "PT" entries.
"""

_T = {
    # ── Language toggle label ─────────────────────────────────────────────────
    "lang_switch": {"EN": "PT", "PT": "EN"},

    # ── Outer tabs ────────────────────────────────────────────────────────────
    "tab_find":   {"EN": "Find schools",  "PT": "Buscar faculdades"},
    "tab_alumni": {"EN": "Famous alumni", "PT": "Ex-alunos famosos"},
    "tab_how":    {"EN": "How it works",  "PT": "Como funciona"},

    # ── Inner view tabs ───────────────────────────────────────────────────────
    "tab_cards": {"EN": "Cards", "PT": "Cartões"},
    "tab_table": {"EN": "Table", "PT": "Tabela"},
    "tab_map":   {"EN": "Map",   "PT": "Mapa"},

    # ── Page title / subtitle ─────────────────────────────────────────────────
    "page_title": {"EN": "College Match", "PT": "College Match"},
    "page_subtitle": {
        "EN": (
            "Find U.S. colleges and junior colleges that fit an international student's "
            "budget, sport, major, and visa needs."
        ),
        "PT": (
            "Encontre faculdades nos EUA compatíveis com o orçamento, esporte, "
            "curso e necessidade de visto de um estudante internacional."
        ),
    },
    "set_filters_caption": {
        "EN": "Set filters with » at the top left of the page.",
        "PT": "Defina os filtros com » no canto superior esquerdo.",
    },

    # ── Summary metrics ───────────────────────────────────────────────────────
    "metric_schools_fit":    {"EN": "Schools that fit",      "PT": "Faculdades compatíveis"},
    "metric_median_cost":    {"EN": "Median cost/yr",        "PT": "Custo mediano/ano"},
    "metric_athletic_schol": {"EN": "Athletic scholarships", "PT": "Bolsas esportivas"},
    "metric_f1_certified":   {"EN": "F-1 certified",         "PT": "Certificadas F-1"},

    # ── Sort options ──────────────────────────────────────────────────────────
    "sort_best_match":   {"EN": "Best match",              "PT": "Melhor compatibilidade"},
    "sort_lowest_cost":  {"EN": "Lowest cost",             "PT": "Menor custo"},
    "sort_highest_grad": {"EN": "Highest graduation rate", "PT": "Maior taxa de formatura"},

    # ── Sidebar section headers ───────────────────────────────────────────────
    "sidebar_must_haves":     {"EN": "Must-haves",      "PT": "Requisitos obrigatórios"},
    "sidebar_must_haves_cap": {
        "EN": "Schools that fail any of these are removed.",
        "PT": "Faculdades que não atendem esses critérios são removidas.",
    },
    "sidebar_preferences":    {"EN": "What matters most", "PT": "O que é mais importante"},
    "sidebar_budget_label":   {
        "EN": "Max the family can pay per year",
        "PT": "Máximo que a família pode pagar por ano",
    },
    "sidebar_sport_label":   {"EN": "Plays a college sport", "PT": "Pratica esporte universitário"},
    "sidebar_major_label":   {"EN": "Preferred major",       "PT": "Área de estudo preferida"},
    "sidebar_f1_label":      {"EN": "Require F-1 certified", "PT": "Exigir certificação F-1"},

    # ── Card badges ───────────────────────────────────────────────────────────
    "badge_f1_yes":       {"EN": "F-1 certified",            "PT": "F-1 certificada"},
    "badge_f1_no":        {"EN": "Not F-1 certified",        "PT": "Sem certificação F-1"},
    "badge_online":       {"EN": "Online only",              "PT": "Somente online"},
    "badge_intl_aid":     {"EN": "Intl aid",                 "PT": "Bolsa p/ internacionais"},
    "badge_aid_most":     {"EN": "Aid for most internationals", "PT": "Bolsa para maioria dos internacionais"},
    "badge_no_intl_aid":  {"EN": "No aid for internationals","PT": "Sem bolsa p/ internacionais"},
    "badge_athletic_aid": {"EN": "Athletic aid",             "PT": "Bolsa esportiva"},
    "badge_entrepreneur": {"EN": "Entrepreneurship",         "PT": "Empreendedorismo"},
    "badge_transfer":     {"EN": "Transfer track",           "PT": "Via de transferência"},
    "badge_reach":        {"EN": "Reach",                    "PT": "Difícil"},
    "badge_target":       {"EN": "Target",                   "PT": "Razoável"},
    "badge_likely":       {"EN": "Likely",                   "PT": "Provável"},
    "badge_ivy":          {"EN": "Ivy League",               "PT": "Ivy League"},
    "badge_notable":      {"EN": "Notable alumni",           "PT": "Ex-alunos notáveis"},
    "badge_merit_schol":  {"EN": "Intl merit scholarship",   "PT": "Bolsa de mérito p/ internacionais"},
    "badge_pitch":        {"EN": "Pitch competitions",       "PT": "Competições de pitch"},

    # ── "How to apply from Brazil" section ───────────────────────────────────
    "apply_heading": {
        "EN": "How to apply from Brazil",
        "PT": "Como se candidatar do Brasil",
    },
    "apply_step1_heading": {
        "EN": "1. Transcripts & credential evaluation",
        "PT": "1. Histórico escolar e avaliação de credenciais",
    },
    "apply_step1_body": {
        "EN": (
            "**Sworn translation (_tradução juramentada_):** All Brazilian school records must be "
            "translated by a sworn translator certified by the state Junta Comercial. "
            "Cost: ~R$ 76.84/lauda in SP (2026 JUCESP table); varies by state.\n\n"
            "**Credential evaluation:** Most U.S. colleges require a course-by-course evaluation "
            "from [WES](https://www.wes.org) (~$186) or [ECE](https://www.ece.org) (~$199). "
            "Check the school's specific requirement."
        ),
        "PT": (
            "**Tradução juramentada:** Todo histórico escolar brasileiro deve ser traduzido por um "
            "tradutor juramentado certificado pela Junta Comercial do estado. "
            "Custo: ~R$ 76,84/lauda em SP (tabela JUCESP 2026); varia por estado.\n\n"
            "**Avaliação de credenciais:** A maioria das faculdades americanas exige avaliação "
            "curso a curso pela [WES](https://www.wes.org) (~US$ 186) ou "
            "[ECE](https://www.ece.org) (~US$ 199). Verifique o requisito específico da faculdade."
        ),
    },
    "apply_step2_heading": {
        "EN": "2. Standardized tests (SAT/ACT)",
        "PT": "2. Testes padronizados (SAT/ACT)",
    },
    "apply_step2_body": {
        "EN": (
            "Many schools are test-optional. If required or to strengthen your application:\n\n"
            "- **SAT:** ~$111 for international students ($68 base + $43 international surcharge). "
            "Register at [satsuite.collegeboard.org](https://satsuite.collegeboard.org/sat/registration/international-testing).\n"
            "- The ENEM is **not** accepted as a substitute by U.S. colleges.\n"
            "- Check the school's admissions page for test policy and accepted score ranges."
        ),
        "PT": (
            "Muitas faculdades são _test-optional_ (teste opcional). "
            "Se exigido ou para fortalecer a candidatura:\n\n"
            "- **SAT:** ~US$ 111 para estudantes internacionais (US$ 68 base + US$ 43 taxa internacional). "
            "Inscreva-se em [satsuite.collegeboard.org](https://satsuite.collegeboard.org/sat/registration/international-testing).\n"
            "- O ENEM **não** é aceito pelas faculdades americanas.\n"
            "- Verifique a política de testes na página de admissões da faculdade."
        ),
    },
    "apply_step3_heading": {
        "EN": "3. English proficiency",
        "PT": "3. Proficiência em inglês",
    },
    "apply_step3_body": {
        "EN": (
            "Non-native speakers must submit a test score. Common options:\n\n"
            "| Test | Approx. cost |\n|------|------|\n"
            "| TOEFL iBT | ~$245 |\n"
            "| IELTS Academic | ~R$ 1,430 (varies by city) |\n"
            "| Duolingo English Test | $70 |\n\n"
            "Check the school's minimum required score and accepted tests."
        ),
        "PT": (
            "Falantes não-nativos de inglês devem enviar pontuação em teste de proficiência. "
            "Opções comuns:\n\n"
            "| Teste | Custo aproximado |\n|-------|------------------|\n"
            "| TOEFL iBT | ~US$ 245 |\n"
            "| IELTS Academic | ~R$ 1.430 (varia por cidade) |\n"
            "| Duolingo English Test | US$ 70 |\n\n"
            "Verifique a pontuação mínima exigida e quais testes a faculdade aceita."
        ),
    },
    "apply_step4_heading": {
        "EN": "4. Application",
        "PT": "4. Candidatura",
    },
    "apply_step4_fee": {
        "EN": "**Application fee:** ${fee}",
        "PT": "**Taxa de inscrição:** US$ {fee}",
    },
    "apply_step4_fee_waiver": {
        "EN": "Fee waiver available — check the admissions page.",
        "PT": "Isenção de taxa disponível — verifique a página de admissões.",
    },
    "apply_step4_fee_unknown": {
        "EN": "**Application fee:** Check the school's admissions page.",
        "PT": "**Taxa de inscrição:** Consulte a página de admissões da faculdade.",
    },
    "apply_step4_deadline": {
        "EN": "**Regular Decision deadline:** {deadline}",
        "PT": "**Prazo para Regular Decision:** {deadline}",
    },
    "apply_step4_deadline_unknown": {
        "EN": "**Deadline:** Check the school's admissions page.",
        "PT": "**Prazo:** Consulte a página de admissões da faculdade.",
    },
    "apply_step4_transfers": {
        "EN": "Transfer admit rate: {rate:.0%} ({admitted:,} admitted / {applied:,} applied, CDS {cds_year})",
        "PT": "Taxa de admissão para transferência: {rate:.0%} ({admitted:,} admitidos / {applied:,} inscritos, CDS {cds_year})",
    },
    "apply_step5_heading": {
        "EN": "5. After admission",
        "PT": "5. Após a admissão",
    },
    "apply_step5_i20": {
        "EN": (
            "**I-20 form:** The school will issue an I-20, which you need to apply for the F-1 student visa.\n\n"
            "**SEVIS fee:** Pay the I-901 SEVIS fee ($350 for F-1) at "
            "[fmjfee.com](https://www.fmjfee.com) before your visa interview.\n\n"
            "**Visa interview:** Schedule at the U.S. Consulate in Brazil. Current fees:\n"
            "- MRV visa application fee: $185 (non-refundable)\n"
            "- No F-1 reciprocity fee for Brazilian nationals"
        ),
        "PT": (
            "**Formulário I-20:** A escola emitirá um I-20, necessário para solicitar o visto de estudante F-1.\n\n"
            "**Taxa SEVIS:** Pague a taxa I-901 do SEVIS (US$ 350 para F-1) em "
            "[fmjfee.com](https://www.fmjfee.com) antes da entrevista consular.\n\n"
            "**Entrevista de visto:** Agende no Consulado americano no Brasil. Taxas atuais:\n"
            "- Taxa MRV de solicitação de visto: US$ 185 (não reembolsável)\n"
            "- Sem taxa de reciprocidade F-1 para brasileiros"
        ),
    },
    "apply_step5_no_f1": {
        "EN": (
            "This school is **not F-1 certified** and cannot issue an I-20. "
            "International students cannot obtain an F-1 student visa to attend this institution."
        ),
        "PT": (
            "Esta faculdade **não é certificada para F-1** e não pode emitir um I-20. "
            "Estudantes internacionais não podem obter visto F-1 para estudar aqui."
        ),
    },
    "apply_costs_caption": {
        "EN": "Fee estimates current as of {date}. Verify before applying.",
        "PT": "Estimativas de taxas vigentes em {date}. Verifique antes de se candidatar.",
    },
}


def t(key: str, lang: str = "EN", **kwargs) -> str:
    """Return the translation for key in lang, falling back to EN, then the key itself."""
    entry = _T.get(key, {})
    text = entry.get(lang) or entry.get("EN") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            pass
    return text


def get_lang() -> str:
    """Return the current UI language from session state (default EN)."""
    try:
        import streamlit as st
        return st.session_state.get("lang", "EN")
    except Exception:
        return "EN"


def all_keys() -> list:
    """Return all translation keys (used in tests to verify coverage)."""
    return list(_T.keys())
