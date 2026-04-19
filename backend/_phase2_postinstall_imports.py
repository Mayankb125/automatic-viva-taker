import importlib
mods = [
    "app.services.pillar2_nlp.question_generator",
    "app.services.pillar3_assessment.semantic_scorer",
    "app.services.pillar3_assessment.depth_scorer",
    "app.services.pillar3_assessment.answer_evaluator",
]
for m in mods:
    try:
        importlib.import_module(m)
        print("OK", m)
    except Exception as e:
        print("FAIL", m, type(e).__name__, e)
