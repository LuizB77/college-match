"""
Translations for the College Match app.

Usage:
    from src.i18n import t, get_lang, SLIDER_OPTIONS_PT
    lang = get_lang()
    heading = t("apply_heading", lang)

Every key must have both "EN" and "PT" entries.
SLIDER_OPTIONS_PT is exported for use in select_slider when lang == "PT".
"""

# Slider option lists — must stay in sync (same length, same index = same intensity).
SLIDER_OPTIONS_EN = ["Don't care", "A little", "Somewhat", "Important", "Very important", "Top priority"]
SLIDER_OPTIONS_PT = ["Indiferente", "Um pouco", "Moderado",  "Importante", "Muito importante",  "Prioridade máxima"]

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

    # ── Sort controls ─────────────────────────────────────────────────────────
    "sort_label":        {"EN": "Sort by",                    "PT": "Ordenar por"},
    "sort_best_match":   {"EN": "Best match",                 "PT": "Melhor compatibilidade"},
    "sort_lowest_cost":  {"EN": "Lowest cost",                "PT": "Menor custo"},
    "sort_highest_grad": {"EN": "Highest graduation rate",    "PT": "Maior taxa de formatura"},

    # ── School lookup ─────────────────────────────────────────────────────────
    "lookup_placeholder": {"EN": "Look up any school...", "PT": "Buscar qualquer faculdade..."},

    # ── Sidebar — Must-haves ──────────────────────────────────────────────────
    "btn_clear_filters": {"EN": "Clear all filters",  "PT": "Limpar todos os filtros"},
    "hdr_must_haves":    {"EN": "Must-haves",          "PT": "Requisitos obrigatórios"},
    "cap_must_haves":    {
        "EN": "Schools that fail any of these are removed.",
        "PT": "Faculdades que não atendem esses critérios são removidas.",
    },
    "lbl_budget": {
        "EN": "Max the family can pay per year",
        "PT": "Máximo que a família pode pagar por ano",
    },
    "cap_no_limit": {
        "EN": "No limit — schools with unknown costs are included.",
        "PT": "Sem limite — faculdades com custos desconhecidos são incluídas.",
    },
    "cap_budget_val": {
        "EN": "Budget: ${val}/yr",
        "PT": "Orçamento: US$ {val}/ano",
    },
    "lbl_need_based": {
        "EN": "Would the family likely qualify for need-based aid?",
        "PT": "A família provavelmente se qualificaria para bolsa por necessidade?",
    },
    "help_need_based": {
        "EN": (
            "'Yes' applies each school's CDS-reported average net cost to the budget filter "
            "for schools that offer need-based aid to internationals. "
            "'No' or 'Not sure' always uses sticker price."
        ),
        "PT": (
            "'Sim' aplica o custo líquido médio reportado pelo CDS ao filtro de orçamento "
            "para faculdades que oferecem bolsa por necessidade a internacionais. "
            "'Não' ou 'Não sei' sempre usa o preço cheio."
        ),
    },
    "opt_need_based_yes":    {"EN": "Yes",      "PT": "Sim"},
    "opt_need_based_no":     {"EN": "No",       "PT": "Não"},
    "opt_need_based_notsure":{"EN": "Not sure", "PT": "Não sei"},

    "lbl_school_types": {"EN": "What type of school?",            "PT": "Qual tipo de faculdade?"},
    "lbl_states":       {"EN": "Where? (leave empty for anywhere)","PT": "Onde? (deixe vazio para qualquer lugar)"},
    "lbl_city_groups":  {"EN": "City size? (leave empty for any)", "PT": "Tamanho da cidade? (deixe vazio para qualquer)"},

    "lbl_plays_sport":  {"EN": "Does the student play a sport?",  "PT": "O estudante pratica um esporte?"},
    "lbl_sport":        {"EN": "Sport",                           "PT": "Esporte"},
    "lbl_gender":       {"EN": "Gender",                          "PT": "Gênero"},
    "opt_gender_men":   {"EN": "men",                             "PT": "Masculino"},
    "opt_gender_women": {"EN": "women",                           "PT": "Feminino"},
    "lbl_scholarship":  {"EN": "Needs an athletic scholarship",   "PT": "Precisa de bolsa esportiva"},

    "lbl_major":   {"EN": "Intended major",       "PT": "Área de estudo pretendida"},
    "lbl_religion":{"EN": "Religious affiliation","PT": "Afiliação religiosa"},
    "help_religion":{
        "EN": (
            "'Any' shows all schools. 'Catholic' = Roman Catholic only. "
            "'Any religious' = schools with a stated affiliation. "
            "'Non-religious' = no stated affiliation."
        ),
        "PT": (
            "'Qualquer' mostra todas as faculdades. 'Católica' = somente Romano Católica. "
            "'Qualquer religiosa' = faculdades com afiliação religiosa declarada. "
            "'Sem afiliação' = sem afiliação religiosa declarada."
        ),
    },
    "opt_affil_any":          {"EN": "Any",           "PT": "Qualquer"},
    "opt_affil_catholic":     {"EN": "Catholic",      "PT": "Católica"},
    "opt_affil_any_religious":{"EN": "Any religious", "PT": "Qualquer religiosa"},
    "opt_affil_non_religious":{"EN": "Non-religious", "PT": "Sem afiliação"},

    # ── Sidebar — Advanced expander ───────────────────────────────────────────
    "lbl_advanced":     {"EN": "Advanced",                                    "PT": "Avançado"},
    "lbl_budget_flex":  {"EN": "Stretch budget for athletes (scholarships expected)", "PT": "Ampliar orçamento para atletas (bolsa esperada)"},
    "help_budget_flex": {
        "EN": "1.5 = consider schools up to 50% over budget (the athlete may receive aid that closes the gap).",
        "PT": "1,5 = considerar faculdades até 50% acima do orçamento (o atleta pode receber bolsa que cobre a diferença).",
    },
    "lbl_min_grad_4yr":  {"EN": "Min grad rate — 4-year", "PT": "Taxa mínima de formatura — 4 anos"},
    "help_min_grad_4yr": {
        "EN": "4-year schools below this are excluded. Schools with unknown rates are kept.",
        "PT": "Faculdades de 4 anos abaixo desse valor são excluídas. Faculdades com taxas desconhecidas são mantidas.",
    },
    "lbl_min_grad_2yr": {"EN": "Min grad rate — 2-year", "PT": "Taxa mínima de formatura — 2 anos"},
    "lbl_strict_major": {
        "EN": "Require exact major (don't count general transfer tracks)",
        "PT": "Exigir curso exato (não contar trilhas gerais de transferência)",
    },
    "help_strict_major": {
        "EN": "When checked, 2-year schools must offer the major as an associate degree; a Liberal Arts transfer track no longer qualifies.",
        "PT": "Quando marcado, faculdades de 2 anos devem oferecer o curso como grau de associado; uma trilha de transferência de Artes Liberais não é qualificada.",
    },
    "lbl_require_f1": {"EN": "Require F-1 eligibility (SEVP certified)", "PT": "Exigir elegibilidade F-1 (certificada SEVP)"},
    "lbl_include_online": {"EN": "Include online-only schools", "PT": "Incluir faculdades somente online"},
    "help_include_online": {
        "EN": "Distance-education-only schools (IPEDS flag). F-1 students must attend in person, so these are excluded by default.",
        "PT": "Faculdades exclusivamente de ensino a distância (flag IPEDS). Estudantes F-1 devem frequentar presencialmente, portanto são excluídas por padrão.",
    },

    "lbl_hidden_gems": {"EN": "Hidden gems only", "PT": "Somente joias escondidas"},
    "help_hidden_gems": {
        "EN": (
            "Schools with top-quarter graduate outcomes, an admit rate ≥ 30%, "
            "and no widely-famous alumni (< 60 Wikipedia languages). "
            "Often excellent schools that families abroad haven't heard of."
        ),
        "PT": (
            "Faculdades com resultados de formandos no quartil superior, taxa de admissão ≥ 30% "
            "e sem ex-alunos amplamente famosos (< 60 idiomas da Wikipedia). "
            "Geralmente ótimas faculdades que famílias no exterior não conhecem."
        ),
    },
    "lbl_intl_merit": {"EN": "Has international merit scholarships", "PT": "Tem bolsas de mérito para internacionais"},
    "help_intl_merit": {
        "EN": (
            "Only schools we've researched so far with a confirmed merit scholarship "
            "open to international students. Schools with no research data are excluded."
        ),
        "PT": (
            "Somente faculdades pesquisadas até agora com bolsa de mérito confirmada "
            "para estudantes internacionais. Faculdades sem dados de pesquisa são excluídas."
        ),
    },

    # ── Sidebar — What matters most ───────────────────────────────────────────
    "hdr_preferences": {"EN": "What matters most", "PT": "O que é mais importante"},
    "cap_preferences": {
        "EN": "These don't remove schools; they decide the order of what's left.",
        "PT": "Esses critérios não removem faculdades; eles decidem a ordem das restantes.",
    },
    "lbl_preset": {"EN": "Start from a preset", "PT": "Começar com um perfil"},

    "preset_balanced":        {"EN": "Balanced",           "PT": "Equilibrado"},
    "preset_budget_first":    {"EN": "Budget first",        "PT": "Custo em primeiro"},
    "preset_athlete_first":   {"EN": "Athlete first",       "PT": "Esporte em primeiro"},
    "preset_academics_first": {"EN": "Academics first",     "PT": "Acadêmico em primeiro"},
    "preset_entrepreneur":    {"EN": "Future entrepreneur", "PT": "Futuro empreendedor"},

    # ── Feature labels (slider headings and chart) ────────────────────────────
    "feature_low_cost":                 {"EN": "Low cost",                   "PT": "Baixo custo"},
    "feature_grad_rate":                {"EN": "Graduation rate",            "PT": "Taxa de formatura"},
    "feature_sport_culture":            {"EN": "Big-time sports",            "PT": "Esporte de alto nível"},
    "feature_athlete_opportunity":      {"EN": "Athlete-friendly campus",    "PT": "Campus amigo do atleta"},
    "feature_international_community":  {"EN": "International students",     "PT": "Estudantes internacionais"},
    "feature_open_admission":           {"EN": "Open admission",             "PT": "Admissão aberta"},
    "feature_small_school":             {"EN": "Small school",               "PT": "Escola pequena"},
    "feature_entrepreneurship_program": {"EN": "Entrepreneurship program",   "PT": "Programa de empreendedorismo"},
    "feature_program_strength":         {"EN": "Strong program in my major", "PT": "Programa forte na minha área"},
    "feature_grad_earnings":            {"EN": "Strong graduate earnings",   "PT": "Boa renda para formandos"},

    # ── Feature help texts ────────────────────────────────────────────────────
    "feature_help_low_cost": {
        "EN": "Cheaper sticker price ranks higher.",
        "PT": "Faculdades com menor mensalidade têm prioridade.",
    },
    "feature_help_grad_rate": {
        "EN": "Schools where more students finish rank higher.",
        "PT": "Faculdades onde mais alunos se formam têm prioridade.",
    },
    "feature_help_sport_culture": {
        "EN": "Schools with large, well-known athletics programs rank higher.",
        "PT": "Faculdades com programas esportivos grandes e conhecidos têm prioridade.",
    },
    "feature_help_athlete_opportunity": {
        "EN": "Schools where athletes are a big share of students (more roster spots, more recruiting).",
        "PT": "Faculdades onde atletas são grande parte do corpo discente (mais vagas no elenco, mais recrutamento).",
    },
    "feature_help_international_community": {
        "EN": "Schools with more international students (usually better support).",
        "PT": "Faculdades com mais estudantes internacionais (geralmente melhor suporte).",
    },
    "feature_help_open_admission": {
        "EN": "Schools that accept everyone rank higher (for weaker academic records).",
        "PT": "Faculdades que aceitam todos têm prioridade (para históricos acadêmicos mais fracos).",
    },
    "feature_help_small_school": {
        "EN": "Smaller schools rank higher.",
        "PT": "Faculdades menores têm prioridade.",
    },
    "feature_help_entrepreneurship_program": {
        "EN": "Schools offering an entrepreneurship degree rank higher.",
        "PT": "Faculdades que oferecem curso de empreendedorismo têm prioridade.",
    },
    "feature_help_program_strength": {
        "EN": "Where graduates in the chosen major earn the most, compared to other schools offering it. With no major chosen: graduates' earnings overall.",
        "PT": "Onde os formandos no curso escolhido ganham mais, em comparação com outras faculdades. Sem área escolhida: rendimentos gerais dos formandos.",
    },

    # ── Slider option values ──────────────────────────────────────────────────
    "slider_dont_care":      {"EN": "Don't care",     "PT": "Indiferente"},
    "slider_a_little":       {"EN": "A little",        "PT": "Um pouco"},
    "slider_somewhat":       {"EN": "Somewhat",        "PT": "Moderado"},
    "slider_important":      {"EN": "Important",       "PT": "Importante"},
    "slider_very_important": {"EN": "Very important",  "PT": "Muito importante"},
    "slider_top_priority":   {"EN": "Top priority",    "PT": "Prioridade máxima"},

    # ── Preferences chart ─────────────────────────────────────────────────────
    "cap_all_dont_care": {
        "EN": "All preferences set to 'Don't care' — results are unranked.",
        "PT": "Todas as preferências definidas como 'Indiferente' — resultados sem classificação.",
    },
    "chart_driving_ranking": {"EN": "What's driving the ranking", "PT": "O que define a classificação"},
    "chart_preference_col":  {"EN": "Preference",                 "PT": "Preferência"},
    "chart_share_col":       {"EN": "Share (%)",                  "PT": "Proporção (%)"},

    # ── Card badges ───────────────────────────────────────────────────────────
    "badge_f1_yes":       {"EN": "F-1 certified",              "PT": "F-1 certificada"},
    "badge_f1_no":        {"EN": "Not F-1 certified",          "PT": "Sem certificação F-1"},
    "badge_online":       {"EN": "Online only",                "PT": "Somente online"},
    "badge_intl_aid":     {"EN": "Intl aid",                   "PT": "Bolsa p/ internacionais"},
    "badge_aid_most":     {"EN": "Aid for most internationals","PT": "Bolsa para maioria dos internacionais"},
    "badge_no_intl_aid":  {"EN": "No aid for internationals",  "PT": "Sem bolsa p/ internacionais"},
    "badge_athletic_aid": {"EN": "Athletic aid",               "PT": "Bolsa esportiva"},
    "badge_entrepreneur": {"EN": "Entrepreneurship",           "PT": "Empreendedorismo"},
    "badge_transfer":     {"EN": "Transfer track",             "PT": "Via de transferência"},
    "badge_reach":        {"EN": "Reach",                      "PT": "Difícil"},
    "badge_target":       {"EN": "Target",                     "PT": "Razoável"},
    "badge_likely":       {"EN": "Likely",                     "PT": "Provável"},
    "badge_ivy":          {"EN": "Ivy League",                 "PT": "Ivy League"},
    "badge_notable":      {"EN": "Notable alumni",             "PT": "Ex-alunos notáveis"},
    "badge_merit_schol":  {"EN": "Intl merit scholarship",     "PT": "Bolsa de mérito p/ internacionais"},
    "badge_pitch":        {"EN": "Pitch competitions",         "PT": "Competições de pitch"},

    # ── Card body text ────────────────────────────────────────────────────────
    "card_aid_full_cover": {
        "EN": "**Aid can cover the full cost** for aided students",
        "PT": "**Bolsa pode cobrir o custo total** para alunos beneficiados",
    },
    "card_per_year":      {"EN": "per year",                          "PT": "por ano"},
    "card_cost_unknown":  {"EN": "**Cost unknown**",                  "PT": "**Custo desconhecido**"},
    "card_est_cost_aided":{
        "EN": "Est. cost if aided · {pct:.0%} of internationals receive aid",
        "PT": "Custo est. se beneficiado · {pct:.0%} dos internacionais recebem bolsa",
    },
    "card_aid_full_cover_pct": {
        "EN": "{pct:.0%} of internationals receive aid",
        "PT": "{pct:.0%} dos internacionais recebem bolsa",
    },
    "card_aid_rare": {
        "EN": "Aid is rare here: only {pct:.0%} of internationals receive it",
        "PT": "Bolsa é rara aqui: apenas {pct:.0%} dos internacionais a recebem",
    },
    "card_aid_pct_avg": {
        "EN": "{pct:.0%} of internationals receive aid",
        "PT": "{pct:.0%} dos internacionais recebem bolsa",
    },
    "card_est_aided_unknown_pct": {
        "EN": "Estimated cost if aided · aid share unknown",
        "PT": "Custo estimado se beneficiado · proporção de bolsas desconhecida",
    },
    "card_sticker_price": {
        "EN": "sticker price before scholarships",
        "PT": "preço bruto antes das bolsas",
    },
    "card_match_score":  {"EN": "Match score: {score:.1f} / 100", "PT": "Pontuação: {score:.1f} / 100"},
    "card_why":          {"EN": "Why: {reasons}",                  "PT": "Por quê: {reasons}"},
    "card_details_btn":  {"EN": "Details",                         "PT": "Detalhes"},
    "card_show_more":    {"EN": "Show {n} more ({rem} remaining)",  "PT": "Mostrar mais {n} ({rem} restantes)"},
    "card_avg_award":    {"EN": "avg {amt}",                        "PT": "média {amt}"},

    # ── Compare table ─────────────────────────────────────────────────────────
    "card_compare_heading": {"EN": "Compare schools",                             "PT": "Comparar faculdades"},
    "card_compare_select":  {
        "EN": "Select up to 3 schools to compare side by side",
        "PT": "Selecione até 3 faculdades para comparar",
    },

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

# ─────────────────────────────────────────────────────────────────────────────
# Lookup helpers
# ─────────────────────────────────────────────────────────────────────────────

# Map WEIGHT_KEYS → i18n key prefix for labels and help
_FEAT_KEY = {
    "low_cost":                "feature_low_cost",
    "grad_rate":               "feature_grad_rate",
    "sport_culture":           "feature_sport_culture",
    "athlete_opportunity":     "feature_athlete_opportunity",
    "international_community": "feature_international_community",
    "open_admission":          "feature_open_admission",
    "small_school":            "feature_small_school",
    "entrepreneurship_program":"feature_entrepreneurship_program",
    "program_strength":        "feature_program_strength",
}

_FEAT_HELP_KEY = {k: f"feature_help_{k}" for k in _FEAT_KEY}

_PRESET_KEY = {
    "Balanced":           "preset_balanced",
    "Budget first":       "preset_budget_first",
    "Athlete first":      "preset_athlete_first",
    "Academics first":    "preset_academics_first",
    "Future entrepreneur":"preset_entrepreneur",
}

_AFFIL_KEY = {
    "Any":           "opt_affil_any",
    "Catholic":      "opt_affil_catholic",
    "Any religious": "opt_affil_any_religious",
    "Non-religious": "opt_affil_non_religious",
}

_NEED_KEY = {
    "Yes":      "opt_need_based_yes",
    "No":       "opt_need_based_no",
    "Not sure": "opt_need_based_notsure",
}

_GENDER_KEY = {
    "men":   "opt_gender_men",
    "women": "opt_gender_women",
}

_SORT_KEY = {
    "Best match":              "sort_best_match",
    "Lowest cost":             "sort_lowest_cost",
    "Highest graduation rate": "sort_highest_grad",
}

_TIER_BADGE_KEY = {
    "Reach":  "badge_reach",
    "Target": "badge_target",
    "Likely": "badge_likely",
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


def feature_label(weight_key: str, lang: str = "EN") -> str:
    """Return the translated display label for a weight key (e.g. 'low_cost')."""
    return t(_FEAT_KEY.get(weight_key, weight_key), lang)


def feature_help(weight_key: str, lang: str = "EN") -> str:
    """Return the translated help text for a weight key."""
    return t(_FEAT_HELP_KEY.get(weight_key, weight_key), lang)


def all_keys() -> list:
    """Return all translation keys (used in tests to verify coverage)."""
    return list(_T.keys())
