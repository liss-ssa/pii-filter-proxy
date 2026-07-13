.PHONY: run test synthetic evaluate pipeline
run:
	uvicorn app.main:app --reload
test:
	pytest
synthetic:
	python scripts/generate_synthetic.py --rows 2500 --seed 42
evaluate:
	python scripts/evaluate.py
pipeline:
	python scripts/run_pipeline.py
