# Plan Realizacji Epica: System Cachowania Nazw Projektów

## 1. Cele i Główne Założenia (Executive Summary)

**Cel Biznesowy:** Zapewnienie stabilnej identyfikacji projektów w sesji Claude Code niezależnie od aktualnego katalogu roboczego, co eliminuje problemy z niespójnością nazw projektów podczas przechodzenia przez podkatalogi.

**Cel Techniczny:** Implementacja systemu inteligentnego cachowania nazw projektów, który:
- Automatycznie wykrywa git root dla projektów
- Tworzy aliasy dla podkatalogów należących do istniejących projektów
- Zapewnia wysoką wydajność poprzez minimalizację git operations
- Gwarantuje thread safety dla concurrent hook calls

**Główne Założenia i Strategia:** Adaptive learning system z cache-first approach, który uczy się struktury projektów automatycznie i zapewnia instant lookup dla cached entries z fallback mechanism dla unknown paths.

### **Kryteria Ukończenia Sekcji:**
- `[ ]` Cel biznesowy i techniczny są jasno sformułowane i mierzalne.
- `[ ]` Wybrana strategia (cache-first z adaptive learning) jest uzasadniona.
- `[ ]` Sekcja jest zrozumiała dla osób nietechnicznych (biznes, Product Owner).

## 2. Definicja Architektury i Zasad Pracy (`PROJECT_BLUEPRINT.MD`)

### **Architektura Rozwiązania:**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Hook Entry Points                          │
│  (notification_hook.py, stop_hook.py, activity_hook.py)        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ get_project_name(cwd)
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                ProjectNameResolver                              │
│  - resolve_project_name(cwd: str) -> str                       │
│  - _lookup_in_cache(cwd: str) -> Optional[str]                 │
│  - _update_cache(cwd: str, project_name: str) -> None          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ProjectCache                                  │
│  - load() -> Dict[str, ProjectInfo]                            │
│  - save(data: Dict[str, ProjectInfo]) -> None                  │
│  - find_project_by_alias(cwd: str) -> Optional[str]            │
│  - add_alias(project_name: str, cwd: str) -> None              │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GitResolver                                   │
│  - get_git_root(cwd: str) -> Optional[str]                     │
│  - get_project_name_from_git_root(git_root: str) -> str        │
└─────────────────────────────────────────────────────────────────┘
```

### **Stos Technologiczny:**
- **Python**: 3.9+ (zgodnie z wymaganiami projektu)
- **Standard Library**: json, os, subprocess, pathlib, threading
- **File System**: `/tmp/claude-monitor/project_cache.json`
- **Version Control**: Git integration dla git root detection
- **Testing**: unittest framework (zgodnie z projektem)

### **Struktura Projektu:**
```
src/shared/
├── project_name_resolver.py    # Main resolver class
├── project_cache.py           # Cache management
├── git_resolver.py            # Git operations
└── project_models.py          # Data models

tests/
├── test_project_name_resolver.py
├── test_project_cache.py
├── test_git_resolver.py
└── test_project_models.py

hooks/
├── notification_hook.py       # Updated to use resolver
├── stop_hook.py              # Updated to use resolver
└── activity_hook.py          # Updated to use resolver
```

### **Konwencje i Standardy:**
- **TDD Approach**: RED-GREEN-REFACTOR dla wszystkich nowych komponentów
- **Naming Convention**: snake_case dla plików i funkcji
- **Error Handling**: Graceful degradation z fallback do basename(cwd)
- **Thread Safety**: Atomic file operations z fcntl lub podobnym mechanizmem
- **Logging**: Konsystentne z istniejącym systemem w projekcie
- **Documentation**: Docstrings dla wszystkich public methods

### **Kryteria Ukończenia Sekcji:**
- `[ ]` Zaproponowana architektura jest kompletna i gotowa do implementacji.
- `[ ]` Stos technologiczny jest zdefiniowany, włącznie z wersjami.
- `[ ]` Zasady pracy są jednoznaczne i nie pozostawiają miejsca na interpretację.

## 3. Analiza Ryzyk i Niejasności

### **Ryzyka Techniczne:**
1. **Cache Corruption**: Plik cache może zostać uszkodzony przez concurrent access
   - *Mitygacja*: Atomic file operations z temporary files + rename
2. **Git Command Failures**: `git rev-parse --show-toplevel` może zawieść
   - *Mitygacja*: Fallback do os.path.basename(os.getcwd())
3. **Performance Impact**: Częste git operations mogą spowalniać hooks
   - *Mitygacja*: Cache-first approach z lazy loading
4. **Memory Leaks**: Cache może rosnąć bez ograniczeń
   - *Mitygacja*: Size limits i periodic cleanup

### **Ryzyka Projektowe:**
1. **Backward Compatibility**: Zmiany w hook interface mogą złamać istniejące funkcjonalności
   - *Mitygacja*: Wrapper approach z gradual migration
2. **Testing Complexity**: Git operations są trudne do unit testowania
   - *Mitygacja*: Mock git operations w testach, integration tests dla real scenarios

### **Kluczowe Pytania do Biznesu/Product Ownera:**
1. Czy system powinien automatycznie czyścić stare wpisy cache? Jeśli tak, po jakim czasie?
2. Czy istnieją specjalne wymagania dotyczące projektów bez git repository?
3. Czy system powinien raportować błędy cache do monitoring systemu?
4. Jaki jest maksymalny akceptowalny rozmiar cache file?

### **Kryteria Ukończenia Sekcji:**
- `[ ]` Każde zidentyfikowane ryzyko ma przypisaną strategię mitygacji.
- `[ ]` Sformułowane pytania są konkretne i wymagają jednoznacznej odpowiedzi.
- `[ ]` Lista jest wyczerpująca i została skonsultowana z potencjalnymi interesariuszami.

## 4. Szczegółowy Plan Działania (Fazy i Zadania)

### **Faza 1: Fundamenty - Data Models i Cache Infrastructure**

#### Zadanie 1.1: Implementacja ProjectInfo data model
- `[x]` **(RED)** Utwórz plik `tests/test_project_models.py` i napisz test sprawdzający tworzenie ProjectInfo z git_root i pustą listą aliases
- `[x]` Uruchom testy i potwierdź, że test nie przechodzi z oczekiwanym błędem
- `[x]` **(GREEN)** Utwórz `src/shared/project_models.py` z klasą ProjectInfo (git_root, aliases)
- `[x]` Uruchom testy i potwierdź, że wszystkie przechodzą
- `[x]` **(REFACTOR)** Dodaj type hints i docstring do ProjectInfo
- `[x]` **(REPEAT)** Dodaj test dla add_alias method i powtórz cykl TDD

#### Zadanie 1.2: Implementacja ProjectCache class
- `[x]` **(RED)** Napisz test sprawdzający load() method z nieistniejącym plikiem cache
- `[x]` Uruchom testy i potwierdź failure
- `[x]` **(GREEN)** Implementuj ProjectCache.load() z fallback do pustego dict
- `[x]` Uruchom testy i potwierdź success
- `[x]` **(REFACTOR)** Optymalizuj error handling
- `[x]` **(REPEAT)** Dodaj testy dla save(), find_project_by_alias(), add_alias()

#### Zadanie 1.3: Atomic file operations dla thread safety
- `[x]` **(RED)** Napisz test sprawdzający concurrent save operations
- `[x]` Uruchom testy i potwierdź race condition
- `[x]` **(GREEN)** Implementuj atomic save z temporary file + rename
- `[x]` Uruchom testy i potwierdź thread safety
- `[x]` **(REFACTOR)** Wyodrębnij atomic operations do utility function

### **Faza 2: Git Integration - Repository Detection**

#### Zadanie 2.1: Implementacja GitResolver class
- `[x]` **(RED)** Utwórz test sprawdzający get_git_root() dla znanego git repository
- `[x]` Uruchom testy i potwierdź failure
- `[x]` **(GREEN)** Implementuj GitResolver.get_git_root() z subprocess call
- `[x]` Uruchom testy i potwierdź success
- `[x]` **(REFACTOR)** Dodaj error handling i timeout dla git commands
- `[x]` **(REPEAT)** Dodaj testy dla edge cases (no git, permission errors)

#### Zadanie 2.2: Project name extraction z git root
- `[x]` **(RED)** Napisz test sprawdzający get_project_name_from_git_root()
- `[x]` Uruchom testy i potwierdź failure
- `[x]` **(GREEN)** Implementuj extraction logic (os.path.basename)
- `[x]` Uruchom testy i potwierdź success
- `[x]` **(REFACTOR)** Dodaj handling dla edge cases (root path, symlinks)

### **Faza 3: Core Resolver - Main Logic Implementation**

#### Zadanie 3.1: Implementacja ProjectNameResolver.resolve_project_name()
- `[x]` **(RED)** Napisz test sprawdzający resolve dla cached path
- `[x]` Uruchom testy i potwierdź failure
- `[x]` **(GREEN)** Implementuj podstawowy lookup flow
- `[x]` Uruchom testy i potwierdź success
- `[x]` **(REFACTOR)** Optymalizuj performance critical paths
- `[x]` **(REPEAT)** Dodaj testy dla cache miss scenarios

#### Zadanie 3.2: Cache miss handling i adaptive learning
- `[x]` **(RED)** Napisz test sprawdzający cache miss + git root detection
- `[x]` Uruchom testy i potwierdź failure
- `[x]` **(GREEN)** Implementuj cache miss logic z git fallback
- `[x]` Uruchom testy i potwierdź success
- `[x]` **(REFACTOR)** Optymalizuj git operations
- `[x]` **(REPEAT)** Dodaj testy dla alias creation logic

#### Zadanie 3.3: Fallback mechanisms
- `[x]` **(RED)** Napisz test sprawdzający fallback do basename przy git failure
- `[x]` Uruchom testy i potwierdź failure
- `[x]` **(GREEN)** Implementuj graceful degradation
- `[x]` Uruchom testy i potwierdź success
- `[x]` **(REFACTOR)** Ujednolic error handling patterns

### **Faza 4: Hook Integration - Refactoring Existing Code**

#### Zadanie 4.1: Refactoring notification_hook.py
- `[ ]` **(RED)** Napisz test sprawdzający get_project_name() w notification_hook
- `[ ]` Uruchom testy i potwierdź że używa starej implementacji
- `[ ]` **(GREEN)** Zastąp os.path.basename(os.getcwd()) wywołaniem ProjectNameResolver
- `[ ]` Uruchom testy i potwierdź że używa nowej implementacji
- `[ ]` **(REFACTOR)** Cleanup starych imports i dead code

#### Zadanie 4.2: Refactoring stop_hook.py
- `[ ]` **(RED)** Napisz test sprawdzający integration z ProjectNameResolver
- `[ ]` Uruchom testy i potwierdź integration
- `[ ]` **(GREEN)** Implementuj changes w stop_hook.py
- `[ ]` Uruchom testy i potwierdź success
- `[ ]` **(REFACTOR)** Ensure consistent error handling

#### Zadanie 4.3: Refactoring activity_hook.py
- `[ ]` **(RED)** Napisz test sprawdzający nową implementację
- `[ ]` Uruchom testy i potwierdź changes
- `[ ]` **(GREEN)** Apply ProjectNameResolver w activity_hook.py
- `[ ]` Uruchom testy i potwierdź success
- `[ ]` **(REFACTOR)** Cleanup i optimization

### **Faza 5: Performance Optimization i Monitoring**

#### Zadanie 5.1: Cache performance monitoring
- `[ ]` **(RED)** Napisz test sprawdzający cache hit/miss metrics
- `[ ]` Uruchom testy i potwierdź failure
- `[ ]` **(GREEN)** Implementuj basic metrics collection
- `[ ]` Uruchom testy i potwierdź success
- `[ ]` **(REFACTOR)** Integrate z existing logging system

#### Zadanie 5.2: Memory management i cleanup
- `[ ]` **(RED)** Napisz test sprawdzający cache size limits
- `[ ]` Uruchom testy i potwierdź failure
- `[ ]` **(GREEN)** Implementuj size-based cleanup
- `[ ]` Uruchom testy i potwierdź success
- `[ ]` **(REFACTOR)** Optimize cleanup algorithms

### **Faza 6: Integration Testing i Deployment**

#### Zadanie 6.1: End-to-end integration tests
- `[ ]` Napisz integration test sprawdzający full flow: new project → cache creation → alias learning
- `[ ]` Napisz integration test sprawdzający concurrent access scenarios
- `[ ]` Napisz integration test sprawdzający graceful degradation przy git failures
- `[ ]` Uruchom wszystkie integration tests i potwierdź success

#### Zadanie 6.2: Backward compatibility verification
- `[ ]` Uruchom istniejące testy hook system i potwierdź że wszystkie przechodzą
- `[ ]` Przetestuj scenariusze z existing cache data
- `[ ]` Zweryfikuj że system działa bez breaking changes

### **Kryteria Ukończenia Sekcji:**
- `[ ]` Wszystkie fazy są logicznie uporządkowane.
- `[ ]` Zadania są "atomowe" - małe i skupione na jednym, konkretnym celu.
- `[ ]` Zadania implementujące logikę są jawnie rozpisane w krokach TDD.
- `[ ]` Każde zadanie jest weryfikowalne (ma jasny cel do osiągnięcia).

## 5. Kryteria Akceptacji i Plan Testów

### **Filozofia Testowania**

**Testuj faktyczne implementacje, nie mocki:** Preferujemy testy integracyjne sprawdzające rzeczywiste interakcje z file system i git operations, aby mieć pewność że cache działa poprawnie w real-world scenarios. Mocki stosujemy tylko do izolowania external dependencies (git commands w niektórych test cases).

**Dogłębne testowanie logiki, pragmatyczne testowanie integration:** Cała logika cachowania i project name resolution musi być w pełni pokryta testami jednostkowymi/integracyjnymi zgodnie z TDD. Hook integration jest testowana głównie przez integration tests sprawdzające end-to-end scenarios.

### **Plan Testów**

#### **Testy Jednostkowe/Integracyjne (TDD):**
- **ProjectCache**: Load/save operations, concurrent access, corruption handling
- **GitResolver**: Git root detection, project name extraction, error scenarios
- **ProjectNameResolver**: Cache lookup, adaptive learning, fallback mechanisms
- **ProjectInfo**: Data model operations, alias management
- **File Operations**: Atomic writes, thread safety, permission handling

#### **Testy E2E (End-to-End):**
1. **New Project Discovery**: Claude enters new git project → cache creates entry → subsequent calls use cached value
2. **Subdirectory Navigation**: Claude navigates to subdirectory → system returns stable project name → alias is created
3. **Cache Persistence**: System restart → cache is loaded → previously learned aliases work correctly
4. **Graceful Degradation**: Git failure → system falls back to basename → continues working
5. **Concurrent Access**: Multiple hooks run simultaneously → cache remains consistent → no race conditions

#### **Testy Manualne/Eksploracyjne:**
- **Performance**: Measure cache hit/miss ratios in real usage scenarios
- **Memory Usage**: Monitor cache file size growth over extended periods
- **Error Recovery**: Test behavior during file system errors, permission issues
- **Cross-Platform**: Verify behavior on different operating systems (if applicable)

### **Kryteria Ukończenia Sekcji:**
- `[ ]` Filozofia testowania jest jasno określona.
- `[ ]` Plan testów jest kompletny i rozróżnia typy testów.
- `[ ]` Zdefiniowano kluczowe scenariusze E2E, które stanowią "definition of done" dla całej funkcjonalności.

## 6. Proponowana Kolejność Realizacji (Roadmap)

### **Sequence Logic:**

1. **Faza 1 → Faza 2**: Data models muszą być gotowe przed git integration
2. **Faza 2 → Faza 3**: Git resolver jest dependency dla main resolver logic
3. **Faza 3 → Faza 4**: Core resolver musi działać przed hook integration
4. **Faza 4 → Faza 5**: Performance optimization wymaga working system
5. **Faza 5 → Faza 6**: Integration testing na końcu potwierdza całość

### **Parallel Opportunities:**
- **Faza 1**: Zadania 1.1 i 1.2 mogą być realizowane równolegle
- **Faza 2**: Zadania 2.1 i 2.2 mogą być realizowane równolegle
- **Faza 4**: Wszystkie hook refactoring tasks mogą być realizowane równolegle
- **Faza 5**: Performance monitoring i memory management mogą być realizowane równolegle

### **Critical Path:**
ProjectInfo → ProjectCache → GitResolver → ProjectNameResolver → Hook Integration → Integration Testing

### **Dependencies:**
- **Git dostępność**: System wymaga git w PATH
- **File system permissions**: Write access do `/tmp/claude-monitor/`
- **Existing hook system**: Musi pozostać functional during transition

### **Kryteria Ukończenia Sekcji:**
- `[ ]` Kolejność jest logiczna i uwzględnia zależności techniczne.
- `[ ]` Zidentyfikowano zadania, które mogą być realizowane równolegle.
- `[ ]` Roadmapa jest logicznie spójna i technicznie wykonalna.
- `[ ]` Brak jakichkolwiek szacowań czasowych (dni, godziny, tygodnie).