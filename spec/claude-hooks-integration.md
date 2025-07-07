# Plan Realizacji Epica: Integracja Claude Code Hooks z Monitorem Sesji

**Dokumentacja Claude Code Hooks:** https://docs.anthropic.com/en/docs/claude-code/hooks

## 1. Cele i Główne Założenia (Executive Summary)

### **Cel Biznesowy:**
Rozszerzyć funkcjonalność monitora sesji Claude o śledzenie aktywności Claude Code w czasie rzeczywistym poprzez integrację z systemem hooks. Użytkownik będzie mógł monitorować nie tylko sesje rozliczeniowe (5-godzinne z ccusage), ale także aktywne sesje pracy z Claude Code, w tym status pracy, oczekiwania na odpowiedź użytkownika i zakończenia sesji.

### **Cel Techniczny:**
Zaimplementować system hooks dla Claude Code, który będzie logował zdarzenia sesji do plików, następnie daemon monitora będzie odczytywał te dane i integrował je z istniejącymi danymi z ccusage. Klient będzie wyświetlał rozszerzoną listę sesji z ikonami reprezentującymi różne stany aktywności.

### **Główne Założenia i Strategia:**
- **Strategia rozdzielenia odpowiedzialności**: Hooks logują zdarzenia → Daemon odczytuje i integruje → Klient wyświetla
- **Backward compatibility**: Zachowanie istniejącej funkcjonalności monitora
- **Rozróżnienie typów sesji**: Sesje rozliczeniowe (ccusage) vs sesje aktywności (Claude Code)
- **Automatyczne czyszczenie**: Usuwanie danych sesji aktywności przy nowym okresie rozliczeniowym

### **Kryteria Ukończenia Sekcji:**
- [x] Cel biznesowy i techniczny są jasno sformułowane i mierzalne
- [x] Wybrana strategia (rozszerzenie istniejącej architektury) jest uzasadniona
- [x] Sekcja jest zrozumiała dla osób nietechnicznych

## 2. Definicja Architektury i Zasad Pracy (PROJECT_BLUEPRINT.MD)

### **Architektura Rozwiązania:**

#### **Nowe Komponenty:**
1. **Hook Scripts (`hooks/`):**
   - `notification_hook.py` - Handler dla zdarzeń Notification
   - `stop_hook.py` - Handler dla zdarzeń Stop/SubagentStop
   - `hook_utils.py` - Wspólne narzędzia dla hooks

2. **Session Activity Tracker (`src/daemon/`):**
   - `session_activity_tracker.py` - Odczyt i przetwarzanie danych z hooks
   - `activity_data_models.py` - Modele danych dla sesji aktywności
   - `hook_log_parser.py` - Parser logów z hooks

3. **Enhanced Client Display (`src/client/`):**
   - Rozszerzenie `display_manager.py` o wyświetlanie sesji aktywności
   - Nowe ikony i statusy sesji

#### **Integracja z Istniejącym Systemem:**
- **Daemon**: Rozszerzenie `data_collector.py` o integrację danych aktywności
- **Data Models**: Dodanie `ActivitySessionData` do `data_models.py`
- **File Manager**: Rozszerzenie o zarządzanie plikami logów hooks

#### **Przepływ Danych:**
```
Claude Code → Hooks → Log Files → Daemon Activity Tracker → Integrated Data → Client Display
                                        ↓
                                   ccusage Data → Data Collector → Integrated Data
```

### **Stos Technologiczny:**
- **Python 3.9+**: Język implementacji (zgodny z istniejącym kodem)
- **JSON**: Format danych dla hooks i logów
- **File System**: Komunikacja między hooks a daemon
- **Claude Code Hooks API**: Notification, Stop, SubagentStop events
- **Existing Stack**: Zachowanie `uv`, `unittest`, standardowa biblioteka

### **Struktura Projektu:**
```
claude-session-monitor/
├── hooks/                          # Nowy katalog
│   ├── notification_hook.py
│   ├── stop_hook.py
│   ├── hook_utils.py
│   └── claude_hooks_config.json    # Konfiguracja hooks
├── src/
│   ├── daemon/
│   │   ├── session_activity_tracker.py  # Nowy
│   │   ├── hook_log_parser.py           # Nowy
│   │   └── data_collector.py            # Rozszerzony
│   ├── shared/
│   │   ├── data_models.py               # Rozszerzony
│   │   └── constants.py                 # Rozszerzony
│   └── client/
│       └── display_manager.py           # Rozszerzony
├── tests/
│   ├── test_hooks/                      # Nowe testy
│   └── test_activity_tracker/           # Nowe testy
└── docs/
    └── hooks_integration.md             # Dokumentacja
```

### **Konwencje i Standardy:**
- **Nazewnictwo**: Prefiksy `activity_` dla komponentów hooks, `hook_` dla utilities
- **Logging**: Strukturyzowane JSON z timestamp, session_id, event_type
- **Error Handling**: Graceful degradation - brak hooks nie wpływa na działanie
- **File Naming**: `claude_activity_YYYY-MM-DD.log` dla logów hooks
- **Git Commits**: Prefix `feat(hooks):` dla nowych funkcji, `fix(hooks):` dla poprawek

### **Kryteria Ukończenia Sekcji:**
- [x] Zaproponowana architektura jest kompletna i gotowa do implementacji
- [x] Stos technologiczny jest zdefiniowany, zgodny z istniejącym
- [x] Struktura projektu uwzględnia nowe komponenty i integrację
- [x] Zasady pracy są jednoznaczne i spójne z istniejącym kodem

## 3. Analiza Ryzyk i Niejasności

### **Ryzyka Techniczne:**
1. **Wydajność**: Odczyt plików logów hooks co 10s może wpłynąć na performance
   - *Mitygacja*: Implementacja cachingu i batch processing, odczyt tylko przy zmianach
2. **Synchronizacja**: Race conditions między hooks zapisującymi a daemon odczytującym
   - *Mitygacja*: Atomic file operations, file locking
3. **Kompatybilność**: Zmiany w Claude Code hooks API mogą złamać integrację
   - *Mitygacja*: Defensive programming, version detection
4. **Rozmiar logów**: Długotrwałe sesje mogą generować duże pliki logów
   - *Mitygacja*: Log rotation, cleanup przy starcie nowego okresu rozliczeniowego

### **Ryzyka Projektowe:**
1. **Złożoność**: Dodanie nowego systemu zwiększa kompleksność kodu
   - *Mitygacja*: Modularny design, comprehensive testing
2. **Maintenance**: Dodatkowe komponenty wymagają więcej utrzymania
   - *Mitygacja*: Automatyczne testy, dokumentacja
3. **User Experience**: Zbyt dużo informacji może przytłoczyć użytkownika
   - *Mitygacja*: Wyświetlanie wszystkich sesji jak uzgodnione, ale z przejrzystym UI
4. **Silent Failures**: Brak możliwości wykrycia czy hooks działają
   - *Mitygacja*: Dokumentacja instalacji, optional feature mindset

### **Kluczowe Pytania do Biznesu/Product Ownera:**
1. **Priorytet wyświetlania**: Które sesje mają być wyświetlane domyślnie - tylko aktywne czy wszystkie?
   - **ODPOWIEDŹ**: Na początek wszystkie sesje aktywności
2. **Retention policy**: Jak długo przechowywać logi hooks - do końca okresu rozliczeniowego czy dłużej?
   - **ODPOWIEDŹ**: Do startu nowego okna rozliczeniowego (5h sesji ccusage)
3. **Performance vs Features**: Czy akceptowalny jest dodatkowy overhead 5-10% CPU dla real-time tracking?
   - **ODPOWIEDŹ**: Nie ma być real-time, odczyt jak z ccusage - raz na 10s
4. **Fallback behavior**: Co powinno się dziać gdy hooks nie działają - ukryć funkcję czy pokazać błąd?
   - **ODPOWIEDŹ**: Brak możliwości wykrycia czy hooks działają, po prostu nie będzie danych aktywności

### **Kryteria Ukończenia Sekcji:**
- [x] Każde zidentyfikowane ryzyko ma przypisaną strategię mitygacji
- [x] Sformułowane pytania są konkretne i wymagają jednoznacznej odpowiedzi
- [x] Lista jest wyczerpująca i uwzględnia aspekty techniczne i biznesowe

## 4. Szczegółowy Plan Działania (Fazy i Zadania)

### **FAZA 1: Fundament - Modele Danych i Infrastruktura** ✅ **UKOŃCZONE**

#### Zadanie 1.1: Implementacja modeli danych dla sesji aktywności
- [x] **(RED)** Utwórz plik testu `test_activity_session_data.py` i napisz pierwszy test sprawdzający tworzenie `ActivitySessionData` z podstawowymi polami (session_id, start_time, status). Test powinien na razie nie przechodzić.
- [x] Uruchom testy i **potwierdź**, że test nie przechodzi z błędem `NameError: name 'ActivitySessionData' is not defined`
- [x] **(GREEN)** Dodaj klasę `ActivitySessionData` do `src/shared/data_models.py` z minimalną implementacją aby test przeszedł
- [x] Uruchom testy i **potwierdź**, że test przechodzi
- [x] **(REFACTOR)** Dodaj pełną implementację klasy z metodami `to_dict()`, `from_dict()`, `validate_schema()`
- [x] **(REPEAT)** Dodaj testy dla różnych statusów sesji (ACTIVE, WAITING, STOPPED) i powtórz cykl RED-GREEN-REFACTOR

#### Zadanie 1.2: Rozszerzenie MonitoringData o dane aktywności
- [x] **(RED)** Napisz test sprawdzający, że `MonitoringData` może przechowywać listę `ActivitySessionData`
- [x] **(GREEN)** Dodaj pole `activity_sessions: List[ActivitySessionData]` do `MonitoringData`
- [x] **(REFACTOR)** Zaktualizuj metody serializacji i walidacji

#### Zadanie 1.3: Dodanie stałych dla hooks
- [x] **(RED)** Napisz test sprawdzający dostępność stałych konfiguracyjnych dla hooks
- [x] **(GREEN)** Dodaj stałe do `src/shared/constants.py`: `HOOK_LOG_DIR`, `HOOK_LOG_FILE_PATTERN`, `ACTIVITY_SESSION_STATUSES`
- [x] **(REFACTOR)** Uporządkuj stałe w logiczne sekcje

### **FAZA 2: Implementacja Hook Scripts** ✅ **UKOŃCZONE**

#### Zadanie 2.1: Stworzenie hook utilities
- [x] **(RED)** Napisz test dla `HookLogger` klasy sprawdzający logowanie zdarzenia do pliku JSON
- [x] **(GREEN)** Stwórz `hooks/hook_utils.py` z klasą `HookLogger` i metodą `log_event()`
- [x] **(REFACTOR)** Dodaj thread-safe file operations i error handling
- [x] **(REPEAT)** Dodaj testy dla różnych typów zdarzeń

#### Zadanie 2.2: Implementacja notification hook
- [x] **(RED)** Napisz test sprawdzający parsowanie danych z Claude Code notification hook
- [x] **(GREEN)** Stwórz `hooks/notification_hook.py` z funkcją `main()` czytającą stdin i logującą zdarzenie
- [x] **(REFACTOR)** Dodaj wykrywanie typu notifikacji i session_id
- [x] **(REPEAT)** Dodaj testy dla różnych typów notyfikacji

#### Zadanie 2.3: Implementacja stop hook
- [x] **(RED)** Napisz test sprawdzający parsowanie danych z Claude Code stop hook
- [x] **(GREEN)** Stwórz `hooks/stop_hook.py` z funkcją `main()` obsługującą Stop i SubagentStop
- [x] **(REFACTOR)** Dodaj rozróżnienie między Stop a SubagentStop
- [x] **(REPEAT)** Dodaj testy dla różnych scenariuszy zakończenia

#### Zadanie 2.4: Konfiguracja hooks dla Claude Code
- [x] Stwórz `hooks/claude_hooks_config.json` z konfiguracją hooks zgodną z dokumentacją Claude Code
- [x] Dodaj instrukcje instalacji hooks w `README.md`
- [x] Przetestuj manualnie działanie hooks z Claude Code

### **FAZA 3: Session Activity Tracker** ✅ **UKOŃCZONE**

#### Zadanie 3.1: Implementacja parsera logów hooks
- [x] **(RED)** Napisz test sprawdzający parsowanie linii logu JSON z hooks
- [x] **(GREEN)** Stwórz `src/daemon/hook_log_parser.py` z klasą `HookLogParser`
- [x] **(REFACTOR)** Dodaj obsługę błędnych formatów i corrupted files
- [x] **(REPEAT)** Dodaj testy dla różnych formatów logów

#### Zadanie 3.2: Implementacja activity tracker
- [x] **(RED)** Napisz test sprawdzający odczyt plików logów i konwersję do `ActivitySessionData`
- [x] **(GREEN)** Stwórz `src/daemon/session_activity_tracker.py` z klasą `SessionActivityTracker`
- [x] **(REFACTOR)** Dodaj caching, file watching i batch processing
- [x] **(REPEAT)** Dodaj testy dla różnych scenariuszy aktywności

#### Zadanie 3.3: Integracja z data collector
- [x] **(RED)** Napisz test sprawdzający, że `DataCollector` łączy dane z ccusage i hooks
- [x] **(GREEN)** Rozszerz `src/daemon/data_collector.py` o wywołanie `SessionActivityTracker`
- [x] **(REFACTOR)** Dodaj error handling i graceful degradation gdy hooks nie działają
- [x] **(REPEAT)** Dodaj testy dla różnych kombinacji danych

#### Zadanie 3.4: Implementacja inteligentnej detekcji statusu sesji
- [x] **(RED)** Napisz test sprawdzający smart status detection na podstawie timing zdarzeń
- [x] **(GREEN)** Dodaj metodę `calculate_smart_status()` do `ActivitySessionData` z logiką czasową
- [x] **(REFACTOR)** Rozszerz `ActivitySessionStatus` o nowe stany: WAITING_FOR_USER, IDLE, INACTIVE
- [x] **(REPEAT)** Zaktualizuj `_merge_sessions()` aby używać smart status detection zamiast prostej logiki

#### Zadanie 3.5: Testowanie integracji z prawdziwym Claude Code
- [x] **(RED)** Skonfiguruj hooks w `~/.claude/settings.json` z PreToolUse/PostToolUse
- [x] **(GREEN)** Przetestuj real-time capture zdarzeń z aktywnym Claude Code
- [x] **(REFACTOR)** Zweryfikuj działanie smart status detection z rzeczywistymi danymi
- [x] **(REPEAT)** Przeprowadź comprehensive testing z 85+ events capture

**Status Fazy 3:** Kompleksowo zrealizowana z dodatkowymi funkcjonalnościami:
- ✅ 26 testów TDD pokrywających wszystkie komponenty
- ✅ Smart status detection z analizą timing (ACTIVE, WAITING_FOR_USER, IDLE, INACTIVE)
- ✅ Real-time integration testing z prawdziwym Claude Code (85+ events)
- ✅ Graceful degradation bez hooks
- ✅ Performance monitoring i statistics
- ✅ Thread-safe operations z RLock

### **FAZA 4: Rozszerzenie Client Display** ✅ **UKOŃCZONE**

#### Zadanie 4.1: Implementacja wyświetlania sesji aktywności
- [x] **(RED)** Napisz test sprawdzający renderowanie listy sesji aktywności z ikonami
- [x] **(GREEN)** Rozszerz `src/client/display_manager.py` o metodę `_render_activity_sessions()`
- [x] **(REFACTOR)** Dodaj konfigurację kolorów i ikon dla różnych statusów
- [x] **(REPEAT)** Dodaj testy dla różnych kombinacji sesji

#### Zadanie 4.2: Integracja wyświetlania z głównym UI
- [x] **(RED)** Napisz test sprawdzający, że główny ekran zawiera sekcję sesji aktywności
- [x] **(GREEN)** Zintegruj `_render_activity_sessions()` z główną metodą `display()`
- [x] **(REFACTOR)** Dodaj opcjonalne wyświetlanie i konfigurację verbosity
- [x] **(REPEAT)** Dodaj testy dla różnych opcji wyświetlania

**Status Fazy 4:** Kompleksowo zrealizowana z rozszerzeniami:
- ✅ 15 nowych testów TDD pokrywających wszystkie funkcjonalności
- ✅ Konfigurowalny system wyświetlania z trzema poziomami szczegółowości (minimal, normal, verbose)
- ✅ Ikony statusów i kolory dla różnych stanów sesji (🔵 ACTIVE, ⏳ WAITING_FOR_USER, 💤 IDLE, ⚫ INACTIVE, ⛔ STOPPED)
- ✅ Integracja z głównym ekranem monitora bez wpływu na istniejącą funkcjonalność
- ✅ Opcjonalne filtrowanie i ograniczenia liczby wyświetlanych sesji
- ✅ Pełna kompatybilność wsteczna z istniejącym systemem

### **FAZA 5: Cleanup i Lifecycle Management** ✅ **UKOŃCZONE**

#### Zadanie 5.1: Implementacja czyszczenia danych ✅ **UKOŃCZONE**
- [x] **(RED)** Napisz test sprawdzający usuwanie starych danych aktywności przy nowym okresie rozliczeniowym
- [x] **(GREEN)** Dodaj metodę `cleanup_completed_billing_sessions()` do `SessionActivityTracker`
- [x] **(REFACTOR)** Dodaj automatyczne czyszczenie po zakończeniu 5h okna billingowego
- [x] **(REPEAT)** Dodaj testy dla różnych scenariuszy czyszczenia

**Implementacja (2025-07-07, 11:10:00):**
- Dodano metodę `cleanup_completed_billing_sessions()` która analizuje czy wszystkie sesje są starsze niż 5h
- Zintegrowano cleanup z `DataCollector._collect_activity_sessions()` - wywołanie po `update_from_log_files()`
- Plik jest czyszczony przez truncation zamiast usuwania, co zapewnia ciągłość działania hook-ów
- Uproszczono architekturę - pojedynczy plik `claude_activity.log` bez datowania

#### Zadanie 5.2: Log rotation i maintenance ✅ **UKOŃCZONE przez design**
- [x] **(RED)** Napisz test sprawdzający rotację plików logów hooks
- [x] **(GREEN)** Zrealizowano przez pojedynczy plik z automatycznym czyszczeniem
- [x] **(REFACTOR)** Brak potrzeby compression - dane czyszczone po 5h oknie
- [x] **(REPEAT)** System automatycznie zarządza rozmiarem pliku przez cleanup

**Realizacja przez uproszczenie architektury:**
- Zrezygnowano z rotacji na rzecz pojedynczego pliku `claude_activity.log`
- Automatyczne czyszczenie po zakończeniu 5h okna billingowego eliminuje potrzebę rotacji
- Prostsze rozwiązanie = mniej błędów i łatwiejsze utrzymanie

### **Kryteria Ukończenia Sekcji:**
- [x] Wszystkie fazy są logicznie uporządkowane z uwzględnieniem zależności
- [x] Zadania są "atomowe" - małe i skupione na jednym, konkretnym celu
- [x] Zadania implementujące logikę są jawnie rozpisane w krokach TDD
- [x] Każde zadanie jest weryfikowalne i ma jasny cel do osiągnięcia

## 5. Kryteria Akceptacji i Plan Testów

### **Filozofia Testowania**
1. **Testuj faktyczne implementacje**: Hooks będą testowane z prawdziwymi plikami JSON, parser logów z rzeczywistymi danymi
2. **Integracja ponad mocki**: Testy aktywności tracker będą używać rzeczywistych plików logów w testowym środowisku
3. **Dogłębne testowanie logiki**: Pełne pokrycie TDD dla parsowania hooks, integracji danych, lifecycle management
4. **Pragmatyczne testowanie UI**: E2E testy sprawdzające kluczowe ścieżki wyświetlania

### **Plan Testów**

#### **Testy Jednostkowe/Integracyjne (TDD):**
- **HookLogParser**: Parsowanie różnych formatów JSON, obsługa błędów
- **SessionActivityTracker**: Odczyt plików, caching, integracja z data collector
- **ActivitySessionData**: Serializacja, walidacja, transformacje
- **Hook Scripts**: Parsowanie stdin, logowanie zdarzeń, error handling

#### **Testy E2E (End-to-End):**
1. **Pełny przepływ aktywności**: Claude Code → Hook → Log → Daemon → Client Display
2. **Integracja z ccusage**: Wyświetlanie sesji rozliczeniowych wraz z sesjami aktywności
3. **Cleanup po okresie rozliczeniowym**: Sprawdzenie usunięcia starych danych aktywności
4. **Graceful degradation**: Działanie systemu gdy hooks nie są skonfigurowane
5. **Performance test**: Sprawdzenie wpływu na wydajność przy wielu aktywnych sesjach

#### **Testy Manualne/Eksploracyjne:**
- **Konfiguracja hooks**: Sprawdzenie instrukcji instalacji i konfiguracji
- **Visual testing**: Poprawność wyświetlania ikon i statusów w różnych terminalach
- **Error scenarios**: Testowanie zachowania przy corrupted log files
- **Resource usage**: Monitorowanie zużycia CPU i RAM podczas działania

### **Kryteria Ukończenia Sekcji:**
- [x] Filozofia testowania jest jasno określona i spójna z istniejącym kodem
- [x] Plan testów jest kompletny i rozróżnia typy testów
- [x] Zdefiniowano kluczowe scenariusze E2E stanowiące "definition of done"
- [x] Uwzględniono testy performance i resource usage

## 6. Proponowana Kolejność Realizacji (Roadmap)

### **Faza 1: Fundament** ✅ **UKOŃCZONE** (Czas: 2-3 dni)
*Niezależna od hooks Claude Code - można implementować równolegle*
- Modele danych i constants
- Podstawowa infrastruktura

### **Faza 2: Hook Scripts** ✅ **UKOŃCZONE** (Czas: 3-4 dni)
*Wymaga dokończenia Fazy 1*
- Implementacja hook utilities
- Notification i stop hooks
- Konfiguracja Claude Code

### **Faza 3: Activity Tracker** ✅ **UKOŃCZONE** (Czas: 4-5 dni)
*Wymaga dokończenia Fazy 1 i 2*
- Parser logów hooks
- Integracja z data collector
- **Smart status detection z timing analysis**
- **Real-time testing z Claude Code**

### **Faza 4: Client Display** ✅ **UKOŃCZONE** (Czas: 2-3 dni)
*Wymaga dokończenia Fazy 1, może być równoległa z Fazą 3*
- Rozszerzenie UI
- Ikony i statusy

### **Faza 5: Cleanup & Maintenance** ✅ **UKOŃCZONE** (Czas: 1 dzień)
*Wymaga dokończenia wszystkich poprzednich faz*
- Automatyczne czyszczenie danych po 5h oknie
- Uproszczona architektura bez rotacji

### **Zadania Równoległe:**
- **Faza 1 + Dokumentacja**: Pisanie dokumentacji podczas implementacji fundamentów
- **Faza 3 + Faza 4**: Activity tracker i client display mogą być rozwijane równolegle
- **Testy**: Każda faza zawiera swoje testy TDD, więc nie ma osobnej fazy testowej

### **Kryteria Ukończenia Sekcji:**
- [x] Kolejność jest logiczna i uwzględnia zależności techniczne
- [x] Zidentyfikowano zadania możliwe do realizacji równolegle
- [x] Roadmapa jest logicznie spójna i technicznie wykonalna
- [x] Oszacowano czas realizacji poszczególnych faz

---

**Status realizacji: 12-13 dni ukończone z 12-17 planowanych** ✅ **PROJEKT UKOŃCZONY**

**Kluczowe punkty kontrolne:**
1. **Milestone 1**: ✅ **UKOŃCZONE** - Działające hook scripts z podstawowymi modelami danych
2. **Milestone 2**: ✅ **UKOŃCZONE** - Integracja activity tracker z daemon + smart status detection
3. **Milestone 3**: ✅ **UKOŃCZONE** - Pełna funkcjonalność wyświetlania w kliencie (Faza 4)
4. **Milestone 4**: ✅ **UKOŃCZONE** - Kompletny system z cleanup i maintenance (Faza 5)

**Dodatkowe osiągnięcia ponad plan:**
- ✅ Smart status detection z timing analysis (WAITING_FOR_USER, IDLE, INACTIVE)
- ✅ Real-time integration testing z Claude Code (85+ events captured)
- ✅ Enhanced testing coverage (26 nowych testów TDD)
- ✅ Performance monitoring i statistics
- ✅ Thread-safe operations z RLock
- ✅ Project-based activity session grouping zamiast session_id
- ✅ Dynamic alignment w display dla lepszego UX
- ✅ Audio signal system dla zmian statusu sesji (osascript, afplay, terminal bell)
- ✅ SSH-compatible audio signals
- ✅ Intelligent screen refresh z wykrywaniem zmian
- ✅ Activity time display w formacie mm:ss
- ✅ Automatic cache invalidation fixes
- ✅ Simplified log architecture bez datowania plików
- ✅ Activity hooks configuration (PreToolUse → activity, Stop → stop)