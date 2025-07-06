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

### **FAZA 1: Fundament - Modele Danych i Infrastruktura**

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

### **FAZA 2: Implementacja Hook Scripts**

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

### **FAZA 3: Session Activity Tracker**

#### Zadanie 3.1: Implementacja parsera logów hooks
- [ ] **(RED)** Napisz test sprawdzający parsowanie linii logu JSON z hooks
- [ ] **(GREEN)** Stwórz `src/daemon/hook_log_parser.py` z klasą `HookLogParser`
- [ ] **(REFACTOR)** Dodaj obsługę błędnych formatów i corrupted files
- [ ] **(REPEAT)** Dodaj testy dla różnych formatów logów

#### Zadanie 3.2: Implementacja activity tracker
- [ ] **(RED)** Napisz test sprawdzający odczyt plików logów i konwersję do `ActivitySessionData`
- [ ] **(GREEN)** Stwórz `src/daemon/session_activity_tracker.py` z klasą `SessionActivityTracker`
- [ ] **(REFACTOR)** Dodaj caching, file watching i batch processing
- [ ] **(REPEAT)** Dodaj testy dla różnych scenariuszy aktywności

#### Zadanie 3.3: Integracja z data collector
- [ ] **(RED)** Napisz test sprawdzający, że `DataCollector` łączy dane z ccusage i hooks
- [ ] **(GREEN)** Rozszerz `src/daemon/data_collector.py` o wywołanie `SessionActivityTracker`
- [ ] **(REFACTOR)** Dodaj error handling i graceful degradation gdy hooks nie działają
- [ ] **(REPEAT)** Dodaj testy dla różnych kombinacji danych

### **FAZA 4: Rozszerzenie Client Display**

#### Zadanie 4.1: Implementacja wyświetlania sesji aktywności
- [ ] **(RED)** Napisz test sprawdzający renderowanie listy sesji aktywności z ikonami
- [ ] **(GREEN)** Rozszerz `src/client/display_manager.py` o metodę `_render_activity_sessions()`
- [ ] **(REFACTOR)** Dodaj konfigurację kolorów i ikon dla różnych statusów
- [ ] **(REPEAT)** Dodaj testy dla różnych kombinacji sesji

#### Zadanie 4.2: Integracja wyświetlania z głównym UI
- [ ] **(RED)** Napisz test sprawdzający, że główny ekran zawiera sekcję sesji aktywności
- [ ] **(GREEN)** Zintegruj `_render_activity_sessions()` z główną metodą `display()`
- [ ] **(REFACTOR)** Dodaj opcjonalne wyświetlanie i konfigurację verbosity
- [ ] **(REPEAT)** Dodaj testy dla różnych opcji wyświetlania

### **FAZA 5: Cleanup i Lifecycle Management**

#### Zadanie 5.1: Implementacja czyszczenia danych
- [ ] **(RED)** Napisz test sprawdzający usuwanie starych danych aktywności przy nowym okresie rozliczeniowym
- [ ] **(GREEN)** Dodaj metodę `cleanup_old_activity_data()` do `SessionActivityTracker`
- [ ] **(REFACTOR)** Dodaj konfigurację retention policy
- [ ] **(REPEAT)** Dodaj testy dla różnych scenariuszy czyszczenia

#### Zadanie 5.2: Log rotation i maintenance
- [ ] **(RED)** Napisz test sprawdzający rotację plików logów hooks
- [ ] **(GREEN)** Dodaj log rotation do `HookLogger`
- [ ] **(REFACTOR)** Dodaj compression i cleanup starych logów
- [ ] **(REPEAT)** Dodaj testy dla różnych scenariuszy rotacji

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

### **Faza 1: Fundament** (Szacowany czas: 2-3 dni)
*Niezależna od hooks Claude Code - można implementować równolegle*
- Modele danych i constants
- Podstawowa infrastruktura

### **Faza 2: Hook Scripts** (Szacowany czas: 3-4 dni)
*Wymaga dokończenia Fazy 1*
- Implementacja hook utilities
- Notification i stop hooks
- Konfiguracja Claude Code

### **Faza 3: Activity Tracker** (Szacowany czas: 4-5 dni)
*Wymaga dokończenia Fazy 1 i 2*
- Parser logów hooks
- Integracja z data collector
- **Można równolegle z Fazą 4**

### **Faza 4: Client Display** (Szacowany czas: 2-3 dni)
*Wymaga dokończenia Fazy 1, może być równoległa z Fazą 3*
- Rozszerzenie UI
- Ikony i statusy

### **Faza 5: Cleanup & Maintenance** (Szacowany czas: 1-2 dni)
*Wymaga dokończenia wszystkich poprzednich faz*
- Log rotation
- Lifecycle management

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

**Całkowity szacowany czas realizacji: 12-17 dni roboczych**

**Kluczowe punkty kontrolne:**
1. **Milestone 1**: Działające hook scripts z podstawowymi modelami danych
2. **Milestone 2**: Integracja activity tracker z daemon
3. **Milestone 3**: Pełna funkcjonalność wyświetlania w kliencie
4. **Milestone 4**: Kompletny system z cleanup i maintenance