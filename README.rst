=========
pytest-qt
=========

pytest-qt is a `pytest`_ plugin that allows programmers to write tests
for `PyQt5`_, `PyQt6`_, and `PySide6`_ applications.

The main usage is to use the ``qtbot`` fixture, responsible for handling ``qApp``
creation as needed and provides methods to simulate user interaction,
like key presses and mouse clicks:


.. code-block:: python

    def test_hello(qtbot):
        widget = HelloWidget()
        qtbot.addWidget(widget)

        # click in the Greet button and make sure it updates the appropriate label
        qtbot.mouseClick(widget.button_greet, qt_api.QtCore.Qt.MouseButton.LeftButton)

        assert widget.greet_label.text() == "Hello!"


.. _PySide6: https://pypi.org/project/PySide6/
.. _PyQt5: https://pypi.org/project/PyQt5/
.. _PyQt6: https://pypi.org/project/PyQt6/
.. _pytest: http://pytest.org

This allows you to test and make sure your view layer is behaving the way you expect after each code change.

.. |version| image:: http://img.shields.io/pypi/v/pytest-qt.svg
  :target: https://pypi.python.org/pypi/pytest-qt

.. |conda-forge| image:: https://img.shields.io/conda/vn/conda-forge/pytest-qt.svg
    :target: https://anaconda.org/conda-forge/pytest-qt

.. |ci| image:: https://github.com/pytest-dev/pytest-qt/workflows/test/badge.svg
  :target: https://github.com/pytest-dev/pytest-qt/actions

.. |coverage| image:: http://img.shields.io/coveralls/pytest-dev/pytest-qt.svg
  :target: https://coveralls.io/r/pytest-dev/pytest-qt

.. |docs| image:: https://readthedocs.org/projects/pytest-qt/badge/?version=latest
  :target: https://pytest-qt.readthedocs.io

.. |python| image:: https://img.shields.io/pypi/pyversions/pytest-qt.svg
  :target: https://pypi.python.org/pypi/pytest-qt/
  :alt: Supported Python versions

.. |ruff| image:: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json
  :target: https://github.com/astral-sh/ruff

|python| |version| |conda-forge| |ci| |coverage| |docs| |ruff|


Features
========

- `qtbot`_ fixture to simulate user interaction with ``Qt`` widgets.
- `Automatic capture`_ of ``qDebug``, ``qWarning`` and ``qCritical`` messages;
- waitSignal_ and waitSignals_ functions to block test execution until specific
  signals are emitted.
- `Exceptions in virtual methods and slots`_ are automatically captured and
  fail tests accordingly.

.. _qtbot: https://pytest-qt.readthedocs.io/en/latest/reference.html#module-pytestqt.qtbot
.. _Automatic capture: https://pytest-qt.readthedocs.io/en/latest/logging.html
.. _waitSignal: https://pytest-qt.readthedocs.io/en/latest/signals.html
.. _waitSignals: https://pytest-qt.readthedocs.io/en/latest/signals.html
.. _Exceptions in virtual methods and slots: https://pytest-qt.readthedocs.io/en/latest/virtual_methods.html

Requirements
============

Works with either PySide6_, PyQt6_ or PyQt5_.

If any of the above libraries is already imported by the time the tests execute, that library will be used.

If not, pytest-qt will try to import and use the Qt APIs, in this order:

- ``PySide6``
- ``PyQt6``
- ``PyQt5``

To force a particular API, set the configuration variable ``qt_api`` in your ``pytest.ini`` file to
``pyside6``, ``pyqt6`` or ``pyqt5``:

.. code-block:: ini

    [pytest]
    qt_api=pyqt6


Alternatively, you can set the ``PYTEST_QT_API`` environment
variable to the same values described above (the environment variable wins over the configuration
if both are set).


Documentation
=============

Full documentation and tutorial available at `Read the Docs`_.

.. _Read The Docs: https://pytest-qt.readthedocs.io

Change Log
==========

Please consult the `changelog page`_.

.. _changelog page: https://pytest-qt.readthedocs.io/en/latest/changelog.html

Bugs/Requests
=============

Please report any issues or feature requests in the `issue tracker`_.

.. _issue tracker: https://github.com/pytest-dev/pytest-qt/issues

Contributing
============

Contributions are welcome, so feel free to submit a bug or feature
request.

Pull requests are highly appreciated! If you
can, include some tests that exercise the new code or test that a bug has been
fixed, and make sure to include yourself in the contributors list. :)

To prepare your environment, create a virtual environment and install ``pytest-qt`` in editable mode with ``dev``
extras::

    $ pip install --editable .[dev]

After that install ``pre-commit`` for pre-commit checks::

    $ pre-commit install

Building from source
--------------------

``pytest-qt`` needs Python 3.9+, Git and at least one Qt binding (PySide6, PyQt6 or PyQt5).
The steps below build this fork's refactored branch from a clean checkout.

macOS / Linux::

    $ git clone https://github.com/Arpi-d3y/pytest-qtd.git
    $ cd pytest-qtd
    $ git switch a2-refactoring-final
    $ python3 -m venv .venv
    $ source .venv/bin/activate
    $ python -m pip install --editable ".[dev]"
    $ python -m pip install PySide6
    $ python -m compileall -q src
    $ QT_QPA_PLATFORM=offscreen python -m pytest tests -q

Windows (PowerShell)::

    > git clone https://github.com/Arpi-d3y/pytest-qtd.git
    > cd pytest-qtd
    > git switch a2-refactoring-final
    > py -m venv .venv
    > .venv\Scripts\Activate.ps1
    > python -m pip install --editable ".[dev]"
    > python -m pip install PySide6
    > python -m compileall -q src
    > $env:QT_QPA_PLATFORM = "offscreen"
    > python -m pytest tests -q

Windows (Command Prompt): activate with ``.venv\Scripts\activate.bat`` and set
the platform with ``set QT_QPA_PLATFORM=offscreen``; the other commands are the same.

Expected result: ``332 passed, 8 skipped, 42 xfailed`` (verified on macOS with PySide6).

``QT_QPA_PLATFORM=offscreen`` runs the GUI tests without opening real windows. It is
needed on machines without a display (CI, servers) and avoids two tests that are sensitive
to the desktop environment: ``test_basics.py::test_wait_window[waitActive-True]`` (window
activation can time out) and ``test_screenshot.py::test_region`` (Retina 2x scaling on
macOS). On Linux, installing ``pytest-xvfb`` (``pip install pytest-xvfb``) also works.

Running tests
-------------

With the environment above active, run the whole suite with::

    $ QT_QPA_PLATFORM=offscreen python -m pytest tests -q

Tests can also be run against several Qt bindings in isolated environments using `tox`_::

    $ tox -e py-pyside6,py-pyqt5

``pytest-qt`` is formatted and linted using `ruff <https://github.com/astral-sh/ruff>`_ and uses
`pre-commit <https://github.com/pre-commit/pre-commit>`_ for linting checks before commits. You
can install ``pre-commit`` locally with::

    $ pip install pre-commit
    $ pre-commit install

Related projects
----------------

- `pytest-xvfb <https://github.com/The-Compiler/pytest-xvfb/>`_ allows to run a virtual xserver (Xvfb) on Linux to avoid GUI elements popping up on the screen or for easy CI testing
- `pytest-qml <https://github.com/jgirardet/pytest-qml>`_ allows running QML tests from pytest

Contributors
------------

Many thanks to:

- Igor T. Ghisi (`@itghisi <https://github.com/itghisi>`_);
- John David Reaver (`@jdreaver <https://github.com/jdreaver>`_);
- Benjamin Hedrich (`@bh <https://github.com/bh>`_);
- Benjamin Audren (`@baudren <https://github.com/baudren>`_);
- Fabio Zadrozny (`@fabioz <https://github.com/fabioz>`_);
- Datalyze Solutions (`@datalyze-solutions <https://github.com/datalyze-solutions>`_);
- Florian Bruhin (`@The-Compiler <https://github.com/The-Compiler>`_);
- Guilherme Quentel Melo (`@gqmelo <https://github.com/gqmelo>`_);
- Francesco Montesano (`@montefra <https://github.com/montefra>`_);
- Roman Yurchak (`@rth <https://github.com/rth>`_)
- Christian Karl (`@karlch <https://github.com/karlch>`_)

**Powered by**

.. |pycharm| image:: https://resources.jetbrains.com/storage/products/company/brand/logos/PyCharm.png
  :target: https://www.jetbrains.com/pycharm
  :width: 400

.. |pydev| image:: http://www.pydev.org/images/pydev_banner3.png
  :target: https://www.pydev.org

|pycharm|

|pydev|

.. _tox: https://tox.readthedocs.io
