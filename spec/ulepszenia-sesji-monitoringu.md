# Plan Realizacji Epica: Ulepszenia Sesji Monitoringu Claude

## 1. Cele i Główne Założenia (Executive Summary)

### Cel Biznesowy:
Poprawa jakości monitoringu sesji Claude poprzez naprawę błędów w logice czyszczenia danych aktywności, poprawę doświadczenia użytkownika podczas przejść między oknami 5-godzinnymi oraz dodanie inteligentnych sugestii timing'u pracy.

### Cel Techniczny:
1. **Naprawienie logiki czyszczenia**: Pliki logów aktywności powinny być automatycznie czyszczone po zakończeniu 5-godzinnego okna rozliczeniowego
2. **Poprawa UX przejść**: Wyeliminowanie "śmieci" na ekranie podczas przejść między oknami przez dodanie pełnego czyszczenia ekranu
3. **Optymalizacja timing'u**: Dodanie inteligentnych sugestii rozpoczynania pracy na podstawie zaokrąglania godzin przez Anthropic
4. **Refaktoryzacja kodu**: Usunięcie nieużywanych plików i komponentów

### Główne Założenia i Strategia:
- **Podejście minimalistyczne**: Wprowadzenie najmniejszej ilości zmian koniecznych do naprawy problemów
- **Zachowanie kompatybilności**: Wszystkie zmiany muszą zachować istniejącą funkcjonalność
- **Test-Driven Development**: Wszystkie nowe funkcjonalności i naprawy testowane metodą TDD
- **Graceful degradation**: System musi działać prawidłowo nawet gdy niektóre komponenty nie są dostępne

### Kryteria Ukończenia Sekcji:
- [x] Cel biznesowy i techniczny są jasno sformułowane i mierzalne
- [x] Wybrana strategia (minimalistyczna refaktoryzacja) jest uzasadniona
- [x] Sekcja jest zrozumiała dla osób nietechnicznych

## 2. Definicja Architektury i Zasad Pracy

### Architektura Rozwiązania:
System claude-session-monitor składa się z trzech głównych komponentów:

1. **Daemon Service** (`src/daemon/`):
   - `claude_daemon.py` - główny proces demona z zarządzaniem cyklem życia
   - `session_activity_tracker.py` - śledzenie sesji aktywności z logiki czyszczenia
   - `data_collector.py` - zbieranie danych z integracji ccusage
   - `display_manager.py` - zarządzanie wyświetlaniem terminal UI

2. **Client Interface** (`src/client/`):
   - `claude_client.py` - główny klient z detekcją demona
   - `data_reader.py` - odczyt danych z plików z cache'owaniem
   - `display_manager.py` - interfejs terminalowy z systemem anti-flicker

3. **Shared Infrastructure** (`src/shared/`):
   - `data_models.py` - modele danych (SessionData, ActivitySessionData)
   - `file_manager.py` - atomowe operacje na plikach z synchronizacją iCloud
   - `constants.py` - konfiguracja stałych

### Stos Technologiczny:
- **Python 3.9+** (wykorzystuje `zoneinfo` ze standardowej biblioteki)
- **Standard Library Only** - brak zewnętrznych zależności Python
- **uv** - zarządzanie pakietami dla developmentu
- **macOS** - system notyfikacji i integracja cron
- **ccusage CLI** - musi być zainstalowany i dostępny w PATH

### Struktura Projektu:
```
claude-session-monitor/
├── src/
│   ├── daemon/           # Usługi w tle
│   ├── client/           # Interfejs klienta
│   └── shared/           # Współdzielona infrastruktura
├── hooks/                # Skrypty hook'ów Claude Code
├── tests/                # Testy jednostkowe i integracyjne
└── spec/                 # Specyfikacje i dokumentacja
```

### Konwencje i Standardy:
- **Kod**: PEP 8 compliance, type hints, docstrings
- **Testy**: TDD z unittest framework, 87+ testów
- **Git**: Conventional commits, feature branches
- **Nazewnictwo**: snake_case dla plików, CamelCase dla klas
- **Logowanie**: Strukturalne logowanie z poziomami
- **Error handling**: Graceful degradation, retry logic

### Kryteria Ukończenia Sekcji:
- [x] Zaproponowana architektura jest kompletna i gotowa do implementacji
- [x] Stos technologiczny jest zdefiniowany, włącznie z wersjami
- [x] Zasady pracy są jednoznaczne i nie pozostawiają miejsca na interpretację

## 3. Analiza Ryzyk i Niejasności

### Ryzyka Techniczne:
1. **Ryzyko utraty danych**: Czyszczenie logów może usunąć ważne informacje
   - **Mitygacja**: Implementacja logiki sprawdzającej czy wszystkie sesje są rzeczywiście poza 5h oknem
2. **Ryzyko konfliktów w dostępie do plików**: Równoczesny dostęp daemon/client
   - **Mitygacja**: Wykorzystanie istniejących mechanizmów file_manager z atomowymi operacjami
3. **Ryzyko błędów w logice czasu**: Błędne obliczenia zaokrąglania godzin
   - **Mitygacja**: Dokładne testowanie różnych przypadków brzegowych

### Ryzyka Projektowe:
1. **Brak dostępu do rzeczywistego API Anthropic**: Niemożność weryfikacji logiki zaokrąglania
   - **Mitygacja**: Implementacja na podstawie obserwacji z dokumentacji
2. **Zmiany w zachowaniu ccusage**: Możliwe zmiany w strukturze danych
   - **Mitygacja**: Defensive programming z fallback'ami

### Kluczowe Pytania do Biznesu/Product Ownera:
1. ✅ **ODPOWIEDŹ**: Logika zaokrąglania godzin przez Anthropic jest prawdopodobnie w dół do pełnych godzin
2. ✅ **ODPOWIEDŹ**: Sugestie timing'u mogą być humorystyczne, z większą listą komunikatów i losowym wyborem
3. ✅ **ODPOWIEDŹ**: Brak dodatkowych przypadków brzegowych dla 5h okna na tym etapie

### Kryteria Ukończenia Sekcji:
- [x] Każde zidentyfikowane ryzyko ma przypisaną strategię mitygacji
- [x] Sformułowane pytania są konkretne i wymagają jednoznacznej odpowiedzi
- [x] Lista jest wyczerpująca i została przeanalizowana pod kątem kompletności

## 4. Szczegółowy Plan Działania (Fazy i Zadania)

### Faza 1: Analiza i Przygotowanie

#### Zadanie 1.1: Analiza nieużywanych plików
- [x] **(RED)** Utwórz test `test_unused_files.py` sprawdzający import'y nieużywanych plików
- [x] Uruchom test i potwierdź, że wykrywa nieużywane pliki
- [x] **(GREEN)** Usuń zidentyfikowane nieużywane pliki: `improved_subprocess_pool.py`, `ccusage_executor.py`, `claude_api_client.py`
- [x] **(REFACTOR)** Usuń odpowiadające im testy i zaktualizuj dokumentację
- [x] Uruchom wszystkie testy i potwierdź, że system działa bez usuniętych plików

#### Zadanie 1.2: Analiza istniejącej logiki czyszczenia
- [x] **(RED)** Utwórz test `test_activity_session_cleanup.py` sprawdzający obecną logikę czyszczenia
- [x] Uruchom test i potwierdź, że wykazuje problem z brakiem czyszczenia po 5h oknie
- [x] **(GREEN)** Przeanalizuj metodę `cleanup_completed_billing_sessions()` w `session_activity_tracker.py`
- [x] **(REFACTOR)** Zadokumentuj obecne zachowanie i zidentyfikuj obszary do naprawy

### Faza 2: Naprawa Logiki Czyszczenia Sesji

#### Zadanie 2.1: Implementacja poprawionej logiki czyszczenia
- [x] **(RED)** Napisz test `test_billing_window_cleanup` sprawdzający czy po zakończeniu 5h okna:
  - Plik `claude_activity.log` zostaje wyczyszczony
  - Sesje aktywności znikają z wyświetlania
  - Dane w pamięci są resetowane
- [x] Uruchom test i potwierdź, że nie przechodzi (obecna logika nie czyści poprawnie)
- [x] **(GREEN)** Zmodyfikuj metodę `cleanup_completed_billing_sessions()` aby:
  - Sprawdzała czy wszystkie sesje są starsze niż 5h
  - Czyściła zawartość pliku `claude_activity.log` (truncate do 0 bajtów)
  - Resetowała cache w pamięci
- [x] Uruchom test i potwierdź, że przechodzi
- [x] **(REFACTOR)** Optymalizuj implementację i dodaj odpowiednie logowanie

#### Zadanie 2.2: Integracja z daemon'em
- [x] **(RED)** Napisz test `test_daemon_cleanup_integration` sprawdzający automatyczne wywoływanie czyszczenia
- [x] Uruchom test i potwierdź, że obecny daemon nie wywołuje czyszczenia automatycznie
- [x] **(GREEN)** Dodaj wywołanie `cleanup_completed_billing_sessions()` w głównej pętli daemon'a
- [x] **(REFACTOR)** Zapewnij że czyszczenie jest wywoływane w odpowiednich momentach

### Faza 3: Poprawa Czyszczenia Ekranu

#### Zadanie 3.1: Implementacja pełnego czyszczenia ekranu przy przejściach
- [ ] **(RED)** Napisz test `test_screen_clear_on_transition` sprawdzający czy:
  - Przy przejściu z aktywnej sesji do "waiting" ekran jest w pełni czyszczony
  - Nie pozostają "śmieci" z poprzedniego stanu
- [ ] Uruchom test i potwierdź, że obecna logika nie czyści ekranu w pełni
- [ ] **(GREEN)** Zmodyfikuj `display_manager.py` aby:
  - Wykrywała przejścia między stanami sesji
  - Wywoływała `clear_screen()` zamiast `move_to_top()` przy przejściach
  - Zachowywała optimizację anti-flicker dla normalnych aktualizacji
- [ ] **(REFACTOR)** Dodaj flagę `_force_clear_needed` do śledzenia kiedy wymagane jest pełne czyszczenie

### Faza 4: Implementacja Sugestii Timing'u

#### Zadanie 4.1: Logika analizy czasu rozpoczynania pracy
- [ ] **(RED)** Napisz test `test_work_timing_suggestions` sprawdzający czy:
  - Dla minut 0-15: losowy wybór z pozytywnych sugestii (np. "Idealny czas na rozpoczęcie pracy!", "Świetny moment na start!")
  - Dla minut 16-30: losowy wybór z umiarkowanie pozytywnych sugestii (np. "Od biedy można zaczynać", "Nie najgorzej, ale mogło być lepiej")
  - Dla minut 31-45: losowy wybór z sceptycznych sugestii (np. "Zaczynanie teraz to średni pomysł", "Hmm, może lepiej poczekać?")
  - Dla minut 46-59: losowy wybór z humorystycznych/krytycznych sugestii (np. "Trzeba być... no cóż, żeby teraz zaczynać", "Seriously? 🤔")
- [ ] Uruchom test i potwierdź, że logika nie istnieje
- [ ] **(GREEN)** Zaimplementuj funkcję `get_work_timing_suggestion()` w `utils.py` z randomizacją
- [ ] **(REFACTOR)** Dodaj konfigurację komunikatów w `constants.py` z listami humorystycznych wiadomości

#### Zadanie 4.2: Integracja z wyświetlaniem
- [ ] **(RED)** Napisz test `test_timing_display_integration` sprawdzający wyświetlanie sugestii
- [ ] Uruchom test i potwierdź, że sugestie nie są wyświetlane
- [ ] **(GREEN)** Zmodyfikuj `render_waiting_display()` aby pokazywała sugestie timing'u
- [ ] **(REFACTOR)** Dodaj odpowiednie kolory i formatowanie dla różnych typów sugestii

### Faza 5: Testy Integracyjne i Finalizacja

#### Zadanie 5.1: Kompleksowe testy integracyjne
- [ ] **(RED)** Napisz test `test_full_session_lifecycle` sprawdzający:
  - Pełny cykl: sesja aktywna → koniec 5h okna → czyszczenie → waiting → nowa sesja
  - Poprawne czyszczenie ekranu przy każdym przejściu
  - Wyświetlanie sugestii timing'u w stanie waiting
- [ ] Uruchom test i potwierdź integrację wszystkich komponentów
- [ ] **(GREEN)** Napraw ewentualne problemy integracyjne
- [ ] **(REFACTOR)** Optymalizuj wydajność i dodaj metryki

#### Zadanie 5.2: Walidacja i dokumentacja
- [ ] **(RED)** Napisz test `test_backward_compatibility` sprawdzający zgodność z poprzednią wersją
- [ ] Uruchom wszystkie testy (87+ testów) i potwierdź, że przechodzą
- [ ] **(GREEN)** Zaktualizuj dokumentację w `CLAUDE.md` i `README.md`
- [ ] **(REFACTOR)** Przejrzyj kod pod kątem code review i optymalizacji

### Kryteria Ukończenia Sekcji:
- [x] Wszystkie fazy są logicznie uporządkowane
- [x] Zadania są "atomowe" - małe i skupione na jednym, konkretnym celu
- [x] Zadania implementujące logikę są jawnie rozpisane w krokach TDD
- [x] Każde zadanie jest weryfikowalne (ma jasny cel do osiągnięcia)

## 5. Kryteria Akceptacji i Plan Testów

### Filozofia Testowania
1. **Testuj faktyczne implementacje, nie mocki**: Preferujemy testy integracyjne testujące interakcję komponentów z prawdziwymi plikami i procesami systemowymi
2. **Dogłębne testowanie logiki, pragmatyczne testowanie UI**: Cała logika biznesowa (czyszczenie, timing, przejścia stanów) w pełni pokryta testami TDD
3. **Graceful degradation testing**: Testy sprawdzające zachowanie systemu przy brakujących komponentach

### Plan Testów

#### Testy Jednostkowe/Integracyjne (TDD):
- **Moduł czyszczenia sesji**: Test logiki 5h okna, czyszczenia plików logów, resetowania cache
- **Moduł sugestii timing'u**: Test wszystkich przedziałów czasowych i generowania odpowiednich komunikatów
- **Moduł przejść ekranu**: Test wykrywania zmian stanu i wywoływania odpowiednich metod czyszczenia
- **Moduł zarządzania plikami**: Test atomowych operacji na plikach logów z concurrent access

#### Testy E2E (End-to-End):
1. **Pełny cykl sesji**: Od rozpoczęcia sesji, przez pracę, do zakończenia 5h okna i czyszczenia
2. **Przejścia między stanami**: Aktywna sesja → waiting → nowa sesja z pełnym czyszczeniem ekranu
3. **Sugestie timing'u**: Wyświetlanie odpowiednich komunikatów w różnych porach dnia
4. **Obsługa błędów**: Zachowanie systemu przy brakujących plikach, błędach uprawnień, itp.
5. **Integracja daemon-client**: Poprawna komunikacja między procesami z aktualizacjami w czasie rzeczywistym

#### Testy Manualne/Eksploracyjne:
- **Testowanie timing'u**: Manualna weryfikacja sugestii w różnych godzinach
- **Testowanie UX**: Sprawdzenie czy nie ma migotania ekranu ani "śmieci"
- **Testowanie edge cases**: Zachowanie przy zmianie strefy czasowej, błędach systemowych
- **Testowanie wydajności**: Sprawdzenie czy system nie zużywa nadmiernie zasobów

### Kryteria Ukończenia Sekcji:
- [x] Filozofia testowania jest jasno określona
- [x] Plan testów jest kompletny i rozróżnia typy testów
- [x] Zdefiniowano kluczowe scenariusze E2E, które stanowią "definition of done"

## 6. Proponowana Kolejność Realizacji (Roadmap)

### Kolejność Wykonania:
1. **Faza 1 (Analiza i Przygotowanie)** - Musi być wykonana pierwsza
   - Czyszczenie codebase'u i analiza istniejącej logiki
   - Zadania można wykonywać równolegle: 1.1 i 1.2

2. **Faza 2 (Naprawa Logiki Czyszczenia)** - Zależna od Fazy 1
   - Najważniejsza funkcjonalność, musi być stabilna przed kolejnymi fazami
   - Zadania sekwencyjne: 2.1 → 2.2

3. **Faza 3 (Poprawa Czyszczenia Ekranu)** - Może być równoległa z Fazą 4
   - Niezależna od logiki czyszczenia, może być implementowana osobno
   - Zadanie atomowe: 3.1

4. **Faza 4 (Implementacja Sugestii Timing'u)** - Może być równoległa z Fazą 3
   - Niezależna funkcjonalność, może być implementowana osobno
   - Zadania sekwencyjne: 4.1 → 4.2

5. **Faza 5 (Testy Integracyjne i Finalizacja)** - Musi być ostatnia
   - Zależna od wszystkich poprzednich faz
   - Zadania sekwencyjne: 5.1 → 5.2

### Zależności Techniczne:
- **Faza 2** musi być ukończona przed **Fazą 5** (testy integracyjne wymagają działającej logiki)
- **Faza 3** i **Faza 4** mogą być implementowane równolegle
- **Zadanie 5.1** wymaga ukończenia wszystkich poprzednich faz
- **Zadanie 5.2** wymaga ukończenia zadania 5.1

### Kryteria Ukończenia Sekcji:
- [x] Kolejność jest logiczna i uwzględnia zależności techniczne
- [x] Zidentyfikowano zadania, które mogą być realizowane równolegle
- [x] Roadmapa jest logicznie spójna i technicznie wykonalna
- [x] Brak jakichkolwiek szacowań czasowych

---

## Podsumowanie

Ten plan realizuje kompleksowe ulepszenia systemu monitoringu sesji Claude, skupiając się na:

1. **Naprawie krytycznych błędów** - logika czyszczenia i wyświetlania
2. **Poprawie user experience** - eliminacja migotania i "śmieci" na ekranie  
3. **Dodaniu inteligentnych funkcji** - sugestie optymalnego timing'u pracy
4. **Refaktoryzacji kodu** - usunięcie nieużywanych komponentów

Wszystkie zmiany są implementowane zgodnie z metodologią TDD, co gwarantuje stabilność i możliwość łatwego utrzymania kodu w przyszłości.