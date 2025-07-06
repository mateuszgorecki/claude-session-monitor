# Plan Realizacji Epica: Refaktoryzacja Architektury Demona Claude Session Monitor

## 1. Cele i Główne Założenia (Executive Summary)

### Cel Biznesowy
Zapewnić stabilną, niezawodną i wydajną architekturę systemu monitoringu sesji Claude, eliminując krytyczne problemy które mogą prowadzić do:
- Utraty danych monitorowania
- Spamu notyfikacji (setki duplikujących się alertów)
- Niestabilności demona i jego crash'ów
- Nieprawidłowego raportowania aktywności użytkownika

### Cel Techniczny
Przeprowadzić kompleksową refaktoryzację kluczowych komponentów systemu:
1. **Zunifikowanie strategii ccusage execution** - konsolidacja 7 różnych sposobów wykonywania ccusage
2. **Eliminacja race conditions** - naprawa problemów synchronizacji w subprocess pool
3. **Implementacja proper notification management** - zapobieganie spamowi notyfikacji
4. **Poprawa resource management** - eliminacja memory leaks i zombie processes

### Główne Założenia i Strategia
- **Incremental Refactoring**: Stopniowe wprowadzanie zmian bez przerywania działania
- **Backward Compatibility**: Zachowanie istniejących API i interface'ów
- **TDD Approach**: Wszystkie nowe komponenty implementowane z testami
- **Production Safety**: Każda zmiana weryfikowana przez testy przed deploym

### Kryteria Ukończenia Sekcji
- `[x]` Cel biznesowy i techniczny są jasno sformułowane i mierzalne
- `[x]` Wybrana strategia (incremental refactoring) jest uzasadniona
- `[x]` Sekcja jest zrozumiała dla osób nietechnicznych (biznes, Product Owner)

## 2. Definicja Architektury i Zasad Pracy (`PROJECT_BLUEPRINT.MD`)

### Architektura Rozwiązania

#### Nowa Architektura CcusageExecutor
```
CcusageExecutor (Strategy Pattern)
├── WrapperScriptStrategy (domyślna)
├── DirectSubprocessStrategy (fallback)
├── OSSystemStrategy (launchd compatibility)
└── APIStrategy (przyszłość)
```

#### Ulepszona Architektura Subprocess Pool
```
ImprovedSubprocessPool
├── TaskManager (proper synchronization)
├── WorkerPool (configurable size)
├── ResultHandler (thread-safe results)
└── ResourceCleaner (memory management)
```

#### Notification Management System
```
NotificationSystem
├── NotificationTracker (rate limiting)
├── NotificationQueue (ordered delivery)
├── ActivityMonitor (true inactivity detection)
└── ConfigurableAlerts (user preferences)
```

### Stos Technologiczny
- **Python**: 3.9+ (existing)
- **Threading**: threading.Event, threading.Lock, queue.Queue
- **Synchronization**: concurrent.futures.Future, threading.Condition
- **Testing**: unittest framework (existing), pytest for new tests
- **Process Management**: subprocess with proper cleanup
- **Configuration**: JSON-based with validation (existing)

### Struktura Projektu
```
src/
├── daemon/
│   ├── ccusage_executor.py          # NEW: Unified ccusage execution
│   ├── improved_subprocess_pool.py  # NEW: Fixed threading issues
│   ├── notification_tracker.py     # NEW: Rate limiting system
│   ├── activity_monitor.py         # NEW: True inactivity detection
│   └── resource_manager.py         # NEW: Memory/process cleanup
├── shared/
│   ├── synchronization.py          # NEW: Sync primitives
│   ├── structured_logging.py       # NEW: Centralized logging
│   └── config_validator.py         # NEW: Enhanced validation
└── tests/
    ├── integration/
    │   ├── test_ccusage_executor.py
    │   ├── test_notification_system.py
    │   └── test_resource_management.py
    └── unit/
        ├── test_subprocess_pool.py
        ├── test_activity_monitor.py
        └── test_config_validation.py
```

### Konwencje i Standardy
- **Naming**: `snake_case` dla Python, `UPPER_CASE` dla stałych
- **Git**: Conventional commits (`feat:`, `fix:`, `refactor:`)
- **Testing**: TDD dla nowych komponentów, minimum 90% coverage
- **Documentation**: Docstrings dla wszystkich public methods
- **Error Handling**: Structured exception handling z proper logging
- **Threading**: Zawsze używać proper synchronization primitives

### Kryteria Ukończenia Sekcji
- `[x]` Zaproponowana architektura jest kompletna i gotowa do implementacji
- `[x]` Stos technologiczny jest zdefiniowany, włącznie z wersjami
- `[x]` Zasady pracy są jednoznaczne i nie pozostawiają miejsca na interpretację

## 3. Analiza Ryzyk i Niejasności

### Ryzyka Techniczne
1. **Breaking Changes Risk**: Refaktoryzacja może wprowadzić regresje
   - **Mitygacja**: Comprehensive testing suite + staged rollout
2. **Performance Impact**: Nowe warstwy abstrakcji mogą wpłynąć na wydajność
   - **Mitygacja**: Performance benchmarks + profiling
3. **Thread Safety Complexity**: Nowe synchronization może wprowadzić deadlocks
   - **Mitygacja**: Careful design + extensive concurrent testing

### Ryzyka Projektowe
1. **Scope Creep**: Refaktoryzacja może rozrosnąć się poza planowane zmiany
   - **Mitygacja**: Strict adherence to priority levels + time boxing
2. **Testing Debt**: Istniejące 87 testów może być insufficient
   - **Mitygacja**: Incremental test expansion + coverage monitoring

### Kluczowe Pytania do Biznesu/Product Ownera
1. **Downtime Tolerance**: Czy można tolerować krótkie przerwy w monitoringu podczas wdrażania?
2. **Rollback Strategy**: Jaka jest polityka rollback w przypadku problemów?
3. **Performance SLA**: Jakie są akceptowalne progi wydajności po refaktoryzacji?
4. **Notification Preferences**: Czy obecne domyślne ustawienia notyfikacji są odpowiednie?

### Kryteria Ukończenia Sekcji
- `[x]` Każde zidentyfikowane ryzyko ma przypisaną strategię mitygacji
- `[x]` Sformułowane pytania są konkretne i wymagają jednoznacznej odpowiedzi
- `[x]` Lista jest wyczerpująca i została skonsultowana z potencjalnymi interesariuszami

## 4. Szczegółowy Plan Działania (Fazy i Zadania)

### Faza 1: Priorytet 1 - Krytyczne Problemy (1-2 tygodnie)

#### Zadanie 1.1: Zunifikowanie strategii ccusage execution

**RED Phase:**
- `[x]` Utwórz plik testu `test_ccusage_executor.py` i napisz pierwszy test sprawdzający, że CcusageExecutor zwraca prawidłowe dane z WrapperScriptStrategy. Test powinien na razie nie przechodzić.
- `[x]` Uruchom testy i potwierdź, że dokładnie ten jeden test faktycznie nie przechodzi z błędem `ModuleNotFoundError: No module named 'ccusage_executor'`.

**GREEN Phase:**
- `[x]` Zaimplementuj minimalną wersję `CcusageExecutor` klasy w `src/daemon/ccusage_executor.py` z podstawową implementacją WrapperScriptStrategy.
- `[x]` Uruchom testy i potwierdź, że pierwszy test przechodzi.

**REFACTOR Phase:**
- `[x]` Dodaj Strategy Pattern interface i zaimplementuj wszystkie strategie (WrapperScript, DirectSubprocess, OSSystem).
- `[x]` Uruchom wszystkie testy i potwierdź, że wciąż przechodzą.

**REPEAT Phase:**
- `[x]` Dodaj testy dla fallback mechanism i error handling.
- `[x]` Zaimplementuj fallback logic w CcusageExecutor.
- `[x]` Przeprowadź refaktoryzację dla czytelności i wydajności.

#### Zadanie 1.2: Naprawienie race conditions w subprocess pool

**RED Phase:**
- `[x]` Utwórz plik testu `test_improved_subprocess_pool.py` i napisz test sprawdzający concurrent access bez race conditions. Test powinien wykrywać obecne race conditions.
- `[x]` Uruchom testy i potwierdź, że test nie przechodzi z błędami związanymi z race conditions.

**GREEN Phase:**
- `[x]` Zaimplementuj `ImprovedSubprocessPool` z proper synchronization używając `threading.Event` i `threading.Lock`.
- `[x]` Uruchom testy i potwierdź, że race condition test przechodzi.

**REFACTOR Phase:**
- `[x]` Zastąp busy waiting proper event-based synchronization.
- `[x]` Dodaj proper task cancellation mechanism.
- `[x]` Uruchom wszystkie testy i potwierdź poprawność.

**REPEAT Phase:**
- `[x]` Dodaj testy dla timeout handling i resource cleanup.
- `[x]` Zaimplementuj timeout logic i cleanup mechanisms.

#### Zadanie 1.3: Implementacja proper notification rate limiting

**RED Phase:**
- `[x]` Utwórz plik testu `test_notification_tracker.py` i napisz test sprawdzający, że duplicate notifications są blokowane przez rate limiting.
- `[x]` Uruchom testy i potwierdź, że test nie przechodzi z błędem o braku NotificationTracker.

**GREEN Phase:**
- `[x]` Zaimplementuj `NotificationTracker` klasy z podstawowym rate limiting.
- `[x]` Uruchom testy i potwierdź, że rate limiting test przechodzi.

**REFACTOR Phase:**
- `[x]` Dodaj configurable cooldown periods i notification types.
- `[x]` Zaimplementuj proper notification state management.
- `[x]` Uruchom wszystkie testy i potwierdź poprawność.

**REPEAT Phase:**
- `[x]` Dodaj testy dla różnych typów notyfikacji i edge cases.
- `[x]` Zaimplementuj advanced notification logic.

### Faza 2: Priorytet 2 - Ważne Problemy (1 tydzień)

#### Zadanie 2.1: Naprawa logiki inactivity detection

**RED Phase:**
- `[ ]` Utwórz plik testu `test_activity_monitor.py` i napisz test sprawdzający prawdziwe śledzenie aktywności użytkownika.
- `[ ]` Uruchom testy i potwierdź, że test nie przechodzi z błędem o braku ActivityMonitor.

**GREEN Phase:**
- `[ ]` Zaimplementuj `ActivityMonitor` klasy z proper activity tracking.
- `[ ]` Uruchom testy i potwierdź, że activity tracking test przechodzi.

**REFACTOR Phase:**
- `[ ]` Dodaj sophisticated inactivity detection logic.
- `[ ]` Zaimplementuj configurable inactivity thresholds.

#### Zadanie 2.2: Dodanie configuration validation

**RED Phase:**
- `[ ]` Utwórz plik testu `test_config_validator.py` i napisz test sprawdzający automatyczną walidację podczas deserializacji.
- `[ ]` Uruchom testy i potwierdź, że test nie przechodzi z błędem o braku ConfigValidator.

**GREEN Phase:**
- `[ ]` Zaimplementuj `ConfigValidator` z automatic validation.
- `[ ]` Uruchom testy i potwierdź, że validation test przechodzi.

**REFACTOR Phase:**
- `[ ]` Dodaj comprehensive validation rules i error handling.
- `[ ]` Zaimplementuj graceful error recovery mechanisms.

#### Zadanie 2.3: Implementacja proper cache invalidation

**RED Phase:**
- `[ ]` Utwórz testy dla cache management sprawdzające proper invalidation i size limits.
- `[ ]` Uruchom testy i potwierdź, że obecne cache implementation nie przechodzi testów.

**GREEN Phase:**
- `[ ]` Zaimplementuj improved cache z monotonic time i size limits.
- `[ ]` Uruchom testy i potwierdź, że cache tests przechodzą.

**REFACTOR Phase:**
- `[ ]` Dodaj LRU eviction policy i cache monitoring.
- `[ ]` Zaimplementuj cache health checks.

### Faza 3: Priorytet 3 - Ulepszenia (3-5 dni)

#### Zadanie 3.1: Dodanie structured logging

**RED Phase:**
- `[ ]` Utwórz testy dla structured logging sprawdzające consistent format i centralized configuration.
- `[ ]` Uruchom testy i potwierdź, że obecne logging nie przechodzi testów.

**GREEN Phase:**
- `[ ]` Zaimplementuj `StructuredLogger` z centralized configuration.
- `[ ]` Uruchom testy i potwierdź, że logging tests przechodzą.

**REFACTOR Phase:**
- `[ ]` Dodaj log rotation, retention policies i performance metrics.
- `[ ]` Zaimplementuj proper log levels i filtering.

#### Zadanie 3.2: Implementacja graceful shutdown sequence

**RED Phase:**
- `[ ]` Utwórz testy dla graceful shutdown sprawdzające proper cleanup sequence.
- `[ ]` Uruchom testy i potwierdź, że obecne shutdown logic nie przechodzi testów.

**GREEN Phase:**
- `[ ]` Zaimplementuj improved shutdown sequence z proper timeouts.
- `[ ]` Uruchom testy i potwierdź, że shutdown tests przechodzą.

**REFACTOR Phase:**
- `[ ]` Dodaj configurable timeouts i resource monitoring.
- `[ ]` Zaimplementuj shutdown progress tracking.

#### Zadanie 3.3: Resource management improvements

**RED Phase:**
- `[ ]` Utwórz testy dla resource cleanup sprawdzające memory leaks i zombie processes.
- `[ ]` Uruchom testy i potwierdź, że obecne resource management nie przechodzi testów.

**GREEN Phase:**
- `[ ]` Zaimplementuj `ResourceManager` z proper cleanup mechanisms.
- `[ ]` Uruchom testy i potwierdź, że resource tests przechodzą.

**REFACTOR Phase:**
- `[ ]` Dodaj resource monitoring, limits i health checks.
- `[ ]` Zaimplementuj automatic resource recovery.

### Kryteria Ukończenia Sekcji
- `[x]` Wszystkie fazy są logicznie uporządkowane
- `[x]` Zadania są "atomowe" - małe i skupione na jednym, konkretnym celu
- `[x]` Zadania implementujące logikę są jawnie rozpisane w krokach TDD
- `[x]` Każde zadanie jest weryfikowalne (ma jasny cel do osiągnięcia)

## 5. Kryteria Akceptacji i Plan Testów

### Filozofia Testowania
1. **Testuj faktyczne implementacje, nie mocki**: Preferujemy testy integracyjne testujące rzeczywiste interakcje komponentów z prawdziwymi zasobami (subprocess, filesystem, threading).
2. **Dogłębne testowanie logiki, pragmatyczne testowanie UI**: Cała logika biznesowa (ccusage execution, notification management, resource cleanup) musi być w pełni pokryta testami TDD. Terminal UI jest testowany głównie przez existing acceptance tests.

### Plan Testów

#### Testy Jednostkowe/Integracyjne (TDD)
- **CcusageExecutor**: Testowanie wszystkich strategii execution i fallback mechanisms
- **ImprovedSubprocessPool**: Testowanie concurrent access, race conditions, timeout handling
- **NotificationTracker**: Testowanie rate limiting, cooldown periods, notification state management
- **ActivityMonitor**: Testowanie true inactivity detection i activity tracking
- **ConfigValidator**: Testowanie automatic validation, error handling, graceful recovery
- **ResourceManager**: Testowanie memory cleanup, process management, resource monitoring

#### Testy E2E (End-to-End)
1. **Pełny cykl daemon lifecycle**: Start daemon → collect data → send notifications → graceful shutdown
2. **Notification system integration**: Trigger conditions → rate limiting → actual notification delivery
3. **Resource management under load**: Multiple concurrent sessions → memory usage monitoring → cleanup verification
4. **Error recovery scenarios**: ccusage failures → fallback strategies → system stability
5. **Configuration changes**: Update config → validation → runtime adaptation

#### Testy Manualne/Eksploracyjne
- **Performance verification**: Memory usage patterns after refactoring
- **Notification user experience**: Actual notification delivery on macOS
- **System integration**: Compatibility with different macOS versions and notification systems

### Kryteria Ukończenia Sekcji
- `[x]` Filozofia testowania jest jasno określona
- `[x]` Plan testów jest kompletny i rozróżnia typy testów
- `[x]` Zdefiniowano kluczowe scenariusze E2E, które stanowią "definition of done" dla całej funkcjonalności

## 6. Proponowana Kolejność Realizacji (Roadmap)

### Tydzień 1: Priorytet 1 - Krytyczne Problemy
**Dni 1-3**: CcusageExecutor unification
- Zależności: Brak (można zacząć od razu)
- Równoległe zadania: Możliwe równoległe tworzenie testów

**Dni 4-5**: Subprocess pool race conditions
- Zależności: Częściowo zależne od CcusageExecutor (shared interfaces)
- Równoległe zadania: Notification rate limiting (niezależne)

**Dni 6-7**: Notification rate limiting
- Zależności: Brak (niezależne od powyższych)
- Równoległe zadania: Możliwe z subprocess pool

### Tydzień 2: Priorytet 2 - Ważne Problemy
**Dni 1-3**: Activity monitor i inactivity detection
- Zależności: Notification rate limiting (integration required)
- Równoległe zadania: Configuration validation (niezależne)

**Dni 4-5**: Configuration validation
- Zależności: Brak (niezależne)
- Równoległe zadania: Cache invalidation (niezależne)

**Dni 6-7**: Cache invalidation improvements
- Zależności: Brak (niezależne)
- Równoległe zadania: Możliwe z innymi zadaniami

### Tydzień 3: Priorytet 3 - Ulepszenia
**Dni 1-2**: Structured logging
- Zależności: Wszystkie poprzednie komponenty (integration required)
- Równoległe zadania: Brak (wymaga integracji)

**Dni 3-4**: Graceful shutdown sequence
- Zależności: Wszystkie poprzednie komponenty (coordination required)
- Równoległe zadania: Resource management (częściowe)

**Dni 5**: Resource management
- Zależności: Wszystkie poprzednie komponenty (cleanup integration)
- Równoległe zadania: Finalizacja testów E2E

### Kryteria Ukończenia Sekcji
- `[x]` Kolejność jest logiczna i uwzględnia zależności techniczne
- `[x]` Zidentyfikowano zadania, które mogą być realizowane równolegle
- `[x]` Roadmapa jest logicznie spójna i technicznie wykonalna

---

**Status dokumentu**: ✅ Kompletny plan gotowy do implementacji
**Szacowany czas realizacji**: 2-3 tygodnie
**Wymagane zasoby**: 1 developer + dostęp do środowiska testowego macOS
**Główne deliverables**: Zrefaktoryzowana architektura demona z eliminated critical issues