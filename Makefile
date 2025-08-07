MININET = mininet/*.py
TEST = mininet/test/*.py
EXAMPLES = mininet/examples/*.py
MN = bin/mn
PYTHON ?= python3
PYMN = $(PYTHON) -B bin/mn
BIN = $(MN)
PYSRC = $(MININET) $(TEST) $(EXAMPLES) $(BIN)
MNEXEC = mnexec
MANPAGES = mn.1 mnexec.1
P8IGN = E251,E201,E302,E202,E126,E127,E203,E226,E402,W504,W503,E731
PREFIX ?= /usr
BINDIR ?= $(PREFIX)/bin
MANDIR ?= $(PREFIX)/share/man/man1
DOCDIRS = doc/html doc/latex
PDF = doc/latex/refman.pdf
CC ?= cc
CFLAGS += -Wall -Wextra

# Virtual environment configuration
VENV_DIR = mininet-venv
VENV_PYTHON = $(VENV_DIR)/bin/python
VENV_PIP = $(VENV_DIR)/bin/pip
VENV_ACTIVATE = $(VENV_DIR)/bin/activate

# Check if we're already in a virtual environment
VENV_ACTIVE := $(shell $(PYTHON) -c "import sys; print('1' if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else '0')")

all: codecheck test

clean:
	rm -rf build dist *.egg-info *.pyc $(MNEXEC) $(MANPAGES) $(DOCDIRS)

clean-venv:
	rm -rf $(VENV_DIR)

clean-all: clean clean-venv

codecheck: $(PYSRC)
	-echo "Running code check"
	util/versioncheck.py
	pyflakes3 $(PYSRC) || pyflakes $(PYSRC)
	pylint --rcfile=.pylint $(PYSRC)
#	Exclude miniedit from pep8 checking for now
	pep8 --repeat --ignore=$(P8IGN) `ls $(PYSRC) | grep -v miniedit.py`

errcheck: $(PYSRC)
	-echo "Running check for errors only"
	pyflakes3 $(PYSRC) || pyflakes $(PYSRC)
	pylint -E --rcfile=.pylint $(PYSRC)

test: $(MININET) $(TEST)
	-echo "Running tests"
	mininet/test/test_nets.py
	mininet/test/test_hifi.py

slowtest: $(MININET)
	-echo "Running slower tests (walkthrough, examples)"
	mininet/test/test_walkthrough.py -v
	mininet/examples/test/runner.py -v

mnexec: mnexec.c $(MN) mininet/net.py
	$(CC) $(CFLAGS) $(LDFLAGS) \
	-DVERSION=\"`PYTHONPATH=. $(PYMN) --version 2>&1`\" $< -o $@

install-mnexec: $(MNEXEC)
	install -D $(MNEXEC) $(BINDIR)/$(MNEXEC)

install-manpages: $(MANPAGES)
	install -D -t $(MANDIR) $(MANPAGES)

# Create virtual environment
$(VENV_DIR):
	@echo "Creating virtual environment in $(VENV_DIR)..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Upgrading pip in virtual environment..."
	$(VENV_PIP) install --upgrade pip
	@echo "Virtual environment created successfully!"
	@echo "To activate manually: source $(VENV_ACTIVATE)"

venv: $(VENV_DIR)

# Install in existing virtual environment (if already active)
install-current-venv: install-mnexec install-manpages
	@if [ "$(VENV_ACTIVE)" = "0" ]; then \
		echo "ERROR: No virtual environment is currently active."; \
		echo "Please activate a virtual environment first, or use 'make install' to create one."; \
		exit 1; \
	fi
	@echo "Installing in currently active virtual environment..."
	pip uninstall -y mininet || true
	pip install .

# Main install target - creates venv if needed, then installs
install: install-mnexec install-manpages
	@if [ "$(VENV_ACTIVE)" = "1" ]; then \
		echo "Installing in currently active virtual environment..."; \
		pip uninstall -y mininet || true; \
		pip install .; \
	else \
		echo "No virtual environment active. Creating and using mininet-venv..."; \
		$(MAKE) $(VENV_DIR); \
		echo "Installing mininet in virtual environment..."; \
		$(VENV_PIP) uninstall -y mininet || true; \
		$(VENV_PIP) install .; \
		echo ""; \
		echo "Installation complete!"; \
		echo "To use mininet, activate the virtual environment:"; \
		echo "  source $(VENV_ACTIVATE)"; \
		echo ""; \
		echo "Or run directly:"; \
		echo "  $(VENV_PYTHON) -m mininet.examples.test"; \
	fi

# Install in the mininet-venv (create if needed)
install-venv: $(VENV_DIR) install-mnexec install-manpages
	@echo "Installing mininet in mininet-venv virtual environment..."
	$(VENV_PIP) uninstall -y mininet || true
	$(VENV_PIP) install .
	@echo ""
	@echo "Installation complete!"
	@echo "To activate: source $(VENV_ACTIVATE)"

# Development install in local venv
develop: $(VENV_DIR) $(MNEXEC) $(MANPAGES)
	install $(MNEXEC) $(BINDIR)
	install $(MANPAGES) $(MANDIR)
	@echo "Installing mininet in development mode..."
	$(VENV_PIP) uninstall -y mininet || true
	$(VENV_PIP) install -e . --no-binary :all:
	@echo ""
	@echo "Development installation complete!"
	@echo "To activate: source $(VENV_ACTIVATE)"

# Legacy system install (not recommended)
install-system: install-mnexec install-manpages
	@echo "WARNING: Installing system-wide. This may conflict with system packages."
	@echo "Consider using 'make install' (creates venv) or 'make install-current-venv' instead."
	@read -p "Continue with system install? [y/N] " -n 1 -r; \
	echo; \
	if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "Installation cancelled."; \
		exit 1; \
	fi
	pip uninstall -y mininet || true
	pip install . --break-system-packages

man: $(MANPAGES)

mn.1: $(MN)
	PYTHONPATH=. help2man -N -n "create a Mininet network." \
	--no-discard-stderr "$(PYMN)" -o $@

mnexec.1: mnexec
	help2man -N -n "execution utility for Mininet." \
	-h "-h" -v "-v" --no-discard-stderr ./$< -o $@

.PHONY: doc
doc: man
	doxygen doc/doxygen.cfg
	make -C doc/latex

# Show current environment status
status:
	@echo "Environment Status:"
	@echo "  Virtual environment active: $(VENV_ACTIVE)"
	@echo "  Local mininet-venv exists: $(shell [ -d $(VENV_DIR) ] && echo 'Yes' || echo 'No')"
	@echo "  Python path: $(shell which $(PYTHON))"
	@echo "  Pip path: $(shell which pip 2>/dev/null || echo 'Not found')"
	@if [ -f $(VENV_ACTIVATE) ]; then \
		echo "  mininet-venv activation: source $(VENV_ACTIVATE)"; \
	fi

# Help target
help:
	@echo "Mininet Makefile targets:"
	@echo ""
	@echo "Build and test:"
	@echo "  all              - Run codecheck and test"
	@echo "  test             - Run basic tests"
	@echo "  slowtest         - Run comprehensive tests"
	@echo "  codecheck        - Run code quality checks"
	@echo ""
	@echo "Installation (recommended):"
	@echo "  install          - Auto-install (creates mininet-venv if needed)"
	@echo "  install-venv     - Install in mininet-venv virtual environment"
	@echo "  develop          - Install in development mode (mininet-venv)"
	@echo ""
	@echo "Virtual environment:"
	@echo "  venv             - Create mininet-venv virtual environment"
	@echo "  status           - Show current environment status"
	@echo ""
	@echo "Other install options:"
	@echo "  install-current-venv - Install in currently active venv"
	@echo "  install-system   - System install (not recommended)"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean            - Clean build artifacts"
	@echo "  clean-venv       - Remove mininet-venv virtual environment"
	@echo "  clean-all        - Clean everything"
	@echo ""
	@echo "Recommended workflow:"
	@echo "  make install     # Creates mininet-venv and installs"
	@echo "  source mininet-venv/bin/activate"
	@echo "  mn --test pingall"