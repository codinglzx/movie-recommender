.PHONY: clean init sample run posters

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "清理完成"

init:
	python3 main.py init

sample:
	python3 main.py sample

posters:
	python3 main.py posters

run:
	python3 app.py