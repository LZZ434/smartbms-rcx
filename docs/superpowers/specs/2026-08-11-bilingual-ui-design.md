# SmartBMS-RCx Bilingual Interface Design

**Date:** 2026-08-11  
**Status:** Approved in conversation  
**Scope:** Streamlit dashboard presentation and downloadable report language

## 1. Goal

Add a user-controlled `中文 / English` language switch to SmartBMS-RCx. The application must open in Chinese by default while retaining a complete English mode. The change must make the dashboard easier to learn from without changing any thermal-model, controller, fault, diagnostic, KPI, or scenario result.

The language switch covers:

- all six page names and navigation controls;
- headings, captions, warnings, metrics, chart headings, buttons, filters, and guided exercises;
- fault names, severity, confidence, evidence, recommendations, alarm messages, and displayed table headings/values;
- HTML and Markdown reports downloaded from the dashboard;
- visible mojibake and broken Unicode punctuation in the current presentation.

Professional identifiers and units remain recognizable in both modes: `BMS`, `RCx`, `AHU`, `BACnet`, `Modbus`, `COP`, `HVAC`, `kW`, `kWh`, and raw point IDs are not translated away.

## 2. Non-goals

- No changes to simulation physics, schedules, controllers, diagnostic thresholds, seeds, or verified KPI values.
- No machine-translation API, network dependency, language model, or browser translation.
- No localization of raw trend-column names, BACnet object identifiers, Modbus registers, point IDs, or exported CSV schemas. These remain stable engineering interfaces.
- No locale-specific number formatting or unit conversion in this version.
- No user-account language persistence. The Streamlit session retains the selected language while it is active.

## 3. Chosen approach

Use a presentation-layer internationalization module backed by explicit English and Simplified Chinese dictionaries.

This is preferred over duplicated Chinese/English render functions because it keeps layout and behavior in one code path. It is preferred over runtime translation because the application remains deterministic, offline, technically consistent, and testable.

The new module will live at `smartbms/i18n.py` and own:

- supported language codes (`zh`, `en`) and display names;
- UI translation keys and interpolation;
- page IDs and localized page labels;
- engineering-domain labels such as scenario names, fault categories, severity, and table headings;
- localization of the four known diagnostic evidence/recommendation patterns and known alarm-message patterns;
- DataFrame display copies whose columns and selected values are localized without mutating source data.

The simulation and diagnostic modules continue to produce their existing canonical English identifiers and raw values. Localization happens only when values are rendered or included in a selected-language report.

## 4. Application behavior

### 4.1 Language selection

The top of the sidebar contains a language selector with two choices:

- `中文`
- `English`

The widget stores the stable language code rather than the visible label and defaults to `zh`. Changing it triggers Streamlit's normal rerun and redraws the current application in the selected language.

Widget keys, internal page IDs, scenario IDs, and fault-category IDs remain language-independent so switching languages does not select a different scenario or diagnostic category accidentally.

### 4.2 Navigation

Replace the current tuple of visible English page names with six stable page IDs:

- `overview`
- `plant_control`
- `energy_optimization`
- `rcx_diagnostics`
- `bms_points_alarms`
- `learning_lab`

The sidebar uses a formatting function to show the localized name. Renderer dispatch uses the stable page ID.

### 4.3 Page content

Every renderer receives the active language code. Static text is resolved through translation keys. Dynamic text is formatted after localization, preserving numeric values and engineering units.

Chinese mode uses concise engineering Chinese rather than literal word-for-word translation. On first use, less familiar terms include the English abbreviation, for example `再调试（RCx）` and `空气处理机组（AHU）`.

Charts keep raw signal names where they act as engineering tags, but chart section titles, explanations, selectors, and supporting table headings are localized. CSV column names remain unchanged.

### 4.4 Diagnostics and alarms

The underlying `DiagnosticFinding` objects stay unchanged. A presentation adapter creates localized display fields for:

- fault category;
- finding title;
- severity;
- evidence sentence;
- estimated impact label;
- recommended action.

Known dynamic numbers embedded in evidence text are preserved. If the adapter encounters an unknown domain string, it displays the original text rather than hiding or corrupting evidence. Automated coverage ensures every currently supported fault and alarm pattern has a Chinese translation.

### 4.5 Downloaded reports

`render_html_report` and `render_markdown_report` gain a language argument while keeping English as the API default for backward compatibility. The dashboard always passes the active language.

Downloaded filenames identify the selected language:

- `smartbms-rcx-report-zh.html` / `.md`
- `smartbms-rcx-report-en.html` / `.md`

Report headings, disclosure, KPI labels, explanatory paragraphs, table headings, findings, actions, model boundaries, and source-anchor descriptions follow the chosen language. Reference names, URLs, identifiers, and numeric results remain unchanged.

The command-line portfolio exporter retains its existing canonical English artifacts and manifest contract in this version. This avoids breaking downstream links and reproducibility checks; bilingual generation remains available through the report-rendering API and dashboard downloads.

## 5. Data flow

1. Streamlit initializes the sidebar language code to `zh`.
2. The active language and stable page ID are selected.
3. The cached deterministic `ScenarioBundle` is loaded exactly as before.
4. The page renderer obtains localized UI strings from `smartbms.i18n`.
5. Raw scenario objects are adapted into localized display-only DataFrames or text.
6. Charts continue to read the original numeric DataFrames.
7. Report buttons pass the active language to the report renderer.

No localized value is written back into the cached scenario bundle.

## 6. Translation integrity and error handling

- English and Chinese UI dictionaries must contain identical keys.
- Placeholder names used by translations must match between languages.
- Missing UI keys are programming errors and fail loudly during tests.
- Unknown domain text falls back to the canonical English source text so evidence is never blank.
- All source files remain UTF-8; existing mojibake in user-visible strings is replaced with correct symbols such as `°C`, `–`, `→`, `×`, and `Σ`.
- Language arguments outside `zh` and `en` raise `ValueError` at the translation boundary.

## 7. Testing strategy

Implementation follows red-green-refactor test-driven development.

Automated tests will cover:

1. English and Chinese dictionaries have identical key sets and matching placeholders.
2. Unsupported language codes are rejected.
3. Stable page IDs produce six unique English and Chinese labels.
4. Chinese is the dashboard default.
5. All four fault categories, severities, titles, evidence patterns, and recommendations localize without losing numbers or units.
6. Display DataFrames localize headings/selected values without mutating their source frames.
7. English and Chinese HTML/Markdown reports contain the correct language, disclosure, unchanged KPI values, and language-specific filename selection.
8. All six pages render without exceptions in both languages through Streamlit `AppTest`.
9. Existing simulation, reporting, and regression tests continue to pass.
10. Source scans reject known mojibake sequences and deprecated Streamlit APIs.

Manual/browser acceptance will verify:

- the app initially opens in Chinese;
- switching to English updates navigation and current-page content;
- switching back to Chinese works without resetting the scenario unexpectedly;
- diagnostic evidence and recommendation are readable in Chinese;
- both report downloads use the expected language and filename;
- the local health endpoint remains `200 / ok` and the browser console has no application errors.

## 8. Acceptance criteria

The feature is complete only when:

- the default visible interface is Chinese;
- one control switches every in-scope dashboard string to English and back;
- no current diagnostic or downloaded-report section remains unintentionally English in Chinese mode;
- professional abbreviations, raw engineering identifiers, units, and CSV schemas remain stable;
- the verified values remain 844.288 kWh baseline, 796.814 kWh optimized, 5.623% simulated saving, 100% optimized occupied comfort, and 4/4 fault detection with 45-minute delay;
- both language modes pass automated six-page rendering and browser acceptance;
- all pre-existing and new tests pass from the project virtual environment.

