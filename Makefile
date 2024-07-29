.PHONY: init
# init development
init:
	python3 -m venv venv

.PHONY: clean
# clean generated files
clean:
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	rm -rf .pytest_cache

.PHONY: benchmark
# benchmark
benchmark:
	python3 camelx/benchmark.py > output.txt

.PHONY: deps
# deps development
deps:
	python3 -m pip install --upgrade pip
	python3 -m pip install --upgrade wheel
	python3 -m pip install --upgrade setuptools
	python3 -m pip install --upgrade twine
	python3 -m pip install --upgrade pyyaml
	python3 -m pip install --upgrade pytest==8.2.2
	python3 -m pip install --upgrade pytest-runner==6.0.1
	python3 -m pip install --upgrade twine
	python3 -m pip install --upgrade build

.PHONY: test
# run tests
test:
	pytest --capture=no

.PHONY: dev-build
# dev-build the library
dev-build:
	python3 setup.py build_ext --inplace

.PHONY: build
# build the library
build:
	python3 setup.py build_ext --inplace
	python3 setup.py bdist_wheel --plat-name=macosx_11_0_arm64 # macOS ARM64
	python3 setup.py bdist_wheel --plat-name=macosx_10_9_x86_64 # macOS x86_64
	python3 setup.py bdist_wheel --plat-name=win_arm64 # Windows ARM64
	python3 setup.py bdist_wheel --plat-name=win_amd64 # Windows x86_64
	python3 setup.py bdist_wheel --plat-name=manylinux_2_17_x86_64 # Linux x86_64
	python3 setup.py bdist_wheel --plat-name=linux_armv7l # Linux ARM32

.PHONY: deploy
# deploy package
deploy:
	python3 -m build
	python3 -m twine upload --repository camelx dist/*

# show help
help:
	@echo ''
	@echo 'Usage:'
	@echo ' make [target]'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-0-9]+:/ { \
	helpMessage = match(lastLine, /^# (.*)/); \
			if (helpMessage) { \
					helpCommand = substr($$1, 0, index($$1, ":")-1); \
					helpMessage = substr(lastLine, RSTART + 2, RLENGTH); \
					printf "\033[36m%-22s\033[0m %s\n", helpCommand,helpMessage; \
			} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help