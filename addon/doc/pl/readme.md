# YATTA (Yet Another Text Translation Addon)

* Autor: Piotr Machacz
* Kompatybilność: NVDA 2025.3 lub nowszy
* Pobierz: [Wersja stabilna](https://github.com/pitermach/YATTA/releases/download/v1.0/YATTA-1.0.nvda-addon)

YATTA to dodatek tłumaczący dla NVDA, który został zoptymalizowany pod kątem tłumaczenia programów i gier w locie. Najważniejsze funkcje obejmują:

* Wsparcie dla wielu usług tłumaczeniowych. Można używać zarówno tradycyjnych – Google Translate, Bing, DeepL, jak i opartych na modelach językowych (LLM) – Ollama, OpenAI, Gemini. Połączenie Ollamy i modelu takiego jak translategemma zapewnia bardzo wysoką jakość tłumaczeń całkowicie offline.
* Tłumaczenie ostatnio wypowiedzianej frazy, zaznaczonego tekstu w dowolnej aplikacji lub na stronie internetowej, albo zawartości schowka. Tłumaczenie może być wypowiedziane głosowo lub umieszczone w wirtualnym buforze dla łatwiejszej nawigacji.
* Automatyczne tłumaczenie wszystkiego, co mówi NVDA, włączane oddzielnie dla każdej aplikacji.
* Dynamiczny system pamięci podręcznej obsługujący wyrażenia regularne, co pozwala na jednorazowe przetłumaczenie ciągów znaków takich jak „You have obtained 30 gold”. Liczby mogą być automatycznie zapisywane w pamięci podręcznej jako wyrażenia regularne.
* Opcje dla poszczególnych aplikacji, umożliwiające dostosowanie języka, promptów dla modeli LLM, pamięci podręcznej i innych ustawień.

## Szybki start

YATTA można zainstalować poprzez otwarcie pliku nvda-addon z menedżera plików lub za pomocą przycisku „Zainstaluj z pliku” w add-on store. Dodatek jest gotowy do użycia natychmiast po instalacji. Domyślnie używany będzie tłumacz Google, a tekst zostanie przetłumaczony na język interfejsu NVDA.

Aby zacząć korzystać z YATTA, wystarczy zapamiętać tylko jeden skrót – NVDA+Shift+T. Naciśnięcie go pozwoli na wykonanie dowolnej z dostępnych akcji tłumaczenia poprzez wpisanie odpowiedniej litery. Na przykład naciśnięcie T przetłumaczy ostatnią rzecz, którą wypowiedział NVDA. W dowolnym momencie po naciśnięciu tego skrótu możesz przejrzeć wszystkie dostępne polecenia, naciskając klawisz Tab. Naciśnięcie Enter na danym poleceniu spowoduje jego aktywację. Naciśnięcie dowolnego innego klawisza spowoduje wyjście z warstwy poleceń.

Aby zmienić ustawienia, takie jak używana usługa lub języki tłumaczenia, otwórz ustawienia NVDA i znajdź kategorię YATTA. Możliwa jest również zmiana niektórych opcji tylko dla konkretnej aplikacji. Więcej informacji o wszystkich dostępnych ustawieniach znajdziesz poniżej.

## Dostępne polecenia

Wszystkie polecenia dostępne w warstwie skrótu NVDA+Shift+T mogą mieć również przypisane dedykowane skróty klawiszowe za pomocą okna dialogowego Zdarzenia wejścia NVDA.

Naciśnij T, aby przetłumaczyć ostatnio wypowiedzianą frazę, S, aby przetłumaczyć zaznaczony tekst w dokumencie lub na stronie internetowej, lub C, aby przetłumaczyć schowek. Naciśnięcie dowolnego z powyższych poleceń z klawiszem Shift spowoduje wyświetlenie tłumaczenia w wirtualnym buforze zamiast jego odczytania na głos.

Naciśnij A, aby przełączyć automatyczne tłumaczenie. Gdy ta opcja jest włączona, YATTA będzie automatycznie tłumaczyć wszystko, co mówi NVDA. Pamiętaj, że wprowadzi to opóźnienie między naciśnięciem klawisza a rozpoczęciem mowy przez NVDA, ponieważ YATTA musi poczekać na zakończenie tłumaczenia. Każdy wypowiedziany tekst jest zapisywany w pamięci podręcznej, więc jeśli NVDA powtórzy ten sam tekst, czas reakcji powinien być znacznie krótszy. To ustawienie jest zapisywane tylko dla aktywnej aplikacji. Oznacza to, że jeśli musisz zrobić coś w innym programie i przełączysz się na niego, tłumaczenie zostanie automatycznie wstrzymane i wznowione, gdy tylko powrócisz.

Naciśnięcie W zamieni miejscami język źródłowy i docelowy. To polecenie zadziała tylko wtedy, gdy język źródłowy nie jest ustawiony na automatyczne wykrywanie. Jeśli skonfigurowałeś określone ustawienia dla aktywnego programu (więcej o tym później), zamiana zostanie wykonana dla tego programu, w przeciwnym razie zmienione zostanie ustawienie globalne.

Naciśnięcie O otworzy ustawienia lokalne dla aktywnego programu, natomiast naciśnięcie E otworzy Edytor pamięci podręcznej. Obie te funkcje zostaną wyjaśnione w osobnych sekcjach.

## Ustawienia

Globalne opcje dla YATTA można zmienić w oknie ustawień NVDA w kategorii YATTA. Niektóre usługi wymagają większej konfiguracji niż inne. Okno dialogowe pokaże tylko te ustawienia, które są odpowiednie dla wybranej usługi tłumaczeniowej.

* Usługa tłumacząca – wybór usługi używanej do tłumaczenia.
* Język źródłowy, Język docelowy – wybór języków, między którymi odbywa się tłumaczenie. Naciśnięcie dowolnego z przycisków wyświetli okno dialogowe pozwalające na wybór języka poprzez jego wpisanie lub wybranie z listy za pomocą strzałek. W przypadku konwencjonalnych usług tłumaczeniowych lista języków jest pobierana z ich serwerów i można wybrać tylko obsługiwany język. W przypadku modeli LLM, jeśli używany jest model przeznaczony do tłumaczeń, taki jak translategemma, lista będzie zawierać wszystkie języki wymienione jako oficjalnie obsługiwane.
* Klucz API – dla usług, które go wymagają, takich jak DeepL, OpenAI i Gemini.
* Adres (dla Ollamy) – domyślnie będzie łączyć się z Ollamą uruchomioną na tym samym komputerze co NVDA.
* Model – dla usług opartych na LLM. Nazwę modelu można wpisać ręcznie lub użyć przycisku „Wybierz model...”, aby wybrać go z listy.
* Prompt systemowy, Prompt użytkownika – prompty wysyłane do usług LLM. Jeśli model ma zalecany domyślny prompt, np. translategemma, można użyć przycisku „Wczytaj domyślne prompty”, aby automatycznie wstawić go do pól. Podczas wprowadzania promptu można użyć następujących zmiennych, które zostaną podstawione podczas tłumaczenia:
    * {SOURCE_LANG} – nazwa języka źródłowego w języku angielskim (np. Japanese)
    * {SOURCE_CODE} – kod języka źródłowego (np. ja)
    * {TARGET_LANG}, {TARGET_CODE} – jak wyżej, ale dla języka docelowego
    * {TEXT} – tekst do przetłumaczenia

* Strumieniuj odpowiedzi – jeśli ta opcja jest zaznaczona, odpowiedzi z usług LLM będą odczytywane na bieżąco w miarę ich napływania, zamiast czekać na pełne tłumaczenie. Zaznaczenie tej opcji znacznie poprawia szybkość reakcji.
* Zapisuj pamięć na dysku przy wychodzeniu – gdy ta opcja jest zaznaczona, pamięć podręczna tłumaczeń jest zapisywana na dysku podczas zamykania NVDA. Wyłączenie tej opcji nadal zachowa tłumaczenia w pamięci RAM, ale nie zapisze ich na dysku. To ustawienie można nadpisać dla poszczególnych aplikacji, np. aby zapisywać pamięć podręczną tylko w określonych programach.
* Oddziwelaj liczby podczas tłumaczenia – jeśli ta opcja jest zaznaczona, każdy tekst zawierający liczby jest automatycznie zapisywany w pamięci podręcznej jako wyrażenie regularne z symbolami zastępczymi dla każdej liczby.
* Automatycznie zamień języki, jeśli tekst jest już w języku docelowym – ta opcja jest dostępna tylko wtedy, gdy używana jest konwencjonalna usługa, a język źródłowy nie jest ustawiony na automatyczne wykrywanie. Jeśli usługa tłumaczeniowa wykryje, że tekst jest już w języku docelowym, tłumaczenie zostanie po cichu wykonane ponownie z zamienionymi językami. Uwaga: wykonywanie tłumaczeń w ten sposób trwa dłużej i wymaga dwukrotnego wysyłania tekstu do usługi, więc jeśli chcesz często wykonywać tłumaczenia z zamianą języków, lepiej zrobić to ręcznie, naciskając W z poziomu warstwy poleceń. Wykrywanie języka może być również mniej dokładne w przypadku krótszych tekstów.
* Odtwarzaj dźwięk podczas długich operacji – jeśli tłumaczenie trwa dłużej i ta opcja jest zaznaczona, co 2 sekundy odtwarzane jest kliknięcie, informujące o tym, że YATTA nadal pracuje nad tłumaczeniem.

Oprócz opcji globalnych, niektóre ustawienia można zmienić dla konkretnej aplikacji, naciskając O w warstwie poleceń. Ustawienia te obejmują język tłumaczenia, prompty, zapisywanie pamięci podręcznej, automatyczne dzielenie liczb i inne. Okno dialogowe zawiera również przycisk Resetuj, który pozwala przywrócić ustawienia programu do globalnych wartości domyślnych.

## Pamięć podręczna tłumaczeń

YATTA przechowuje pamięć podręczną każdego przetłumaczonego sformułowania. Pamięć podręczna jest zapisywana oddzielnie dla każdego języka i każdego programu. Istnieją dwa rodzaje wpisów w pamięci podręcznej. Większość wpisów po prostu przypisuje konkretną frazę do jej tłumaczenia w danym języku. To większość wpisów tworzonych przez YATTA.

Ponad to, wpis pamięci podręcznej może zostać dodany jako wyrażenie regularne. Jest to przydatne w sytuacjach, gdy dany tekst pojawia się bardzo często, ale z niewielkimi zmianami. Na przykład komunikaty takie jak „You made it to level 4 and scored 42000 points” mogą zostać zapisane raz, z oznaczeniem liczb jako grupy przechwytującej. Usługa tłumaczeniowa zobaczy wtedy tekst jako „You made it to level <token1> and scored <token2> points. Kiedy YATTA zobaczy te tokeny w tłumaczeniach, będzie wiedzieć, gdzie wstawić liczby. Od tego momentu, nawet jeśli poziom lub liczba punktów zmieni się w tym komunikacie, YATTA nie będzie musiała tłumaczyć go ponownie. Ponieważ ciągi znaków ze zmieniającymi się liczbami pojawiają się bardzo często, zwłaszcza w grach, YATTA zawiera funkcję automatycznego dzielenia liczb podczas tłumaczenia, która wykrywa i zapisuje taki tekst jako wyrażenia regularne. Funkcję pamięci podręcznej można jednak dalej dostosowywać, dodając lub edytując wpisy ręcznie. Można to zrobić w edytorze pamięci podręcznej, dostępnym po naciśnięciu E w warstwie poleceń.

Aby pokazać wszystkie możliwości, posłużmy się przykładem z popularnej gry Crazy party, która pokazuje przeciwników przed pojedyńkiem takim tekstem:

the azure viper, ""poison"" type, with 20 health points and 40 cards in their deck.

Automatyczne wykrywanie liczb utworzyłoby już wpis, który pasowałby do „azure viper” z dowolną ilością zdrowia i kart, ale możliwe jest zmodyfikowanie wpisu tak, aby pasował do dowolnego przeciwnika, tłumacząc jego nazwę i typ osobno. Aby to zrobić, możesz nacisnąć przycisk Dodaj lub Edytuj w edytorze pamięci podręcznej. Okno edycji wpisu jest bardzo proste i ma tylko 3 pola – pola edycji dla tekstu źródłowego i tłumaczenia oraz pole wyboru oznaczające wpis jako wyrażenie regularne.

W naszym przykładzie tekst źródłowy wygląda następująco

```

^(.+), ("".+"" type), with (-?\\d+(?:\[.,/\]\\d+)*) health points and (-?\\d+(?:\[.,/\]\\d+)*) cards in their deck\.$


```

Następnie, wprowadzając wynik tłumaczenia, możesz użyć wpisanych grup na jeden z dwóch sposobów. Jeśli wpiszesz {T1}, {T2}, {T3}… tekst zostanie przetłumaczony osobno, a tłumaczenie zostanie wstawione w miejsce tokenu. Jeśli wpiszesz {P4}, {P5}, {P6}… tekst zostanie wstawiony bez tłumaczenia, co jest szczególnie przydatne w przypadku liczb.

Przykładowe tłumaczenie na Polski wygląda następująco:

```

{T1}, {T2}, {P3} punktów życia i {P4} kart w swojej talii.


```

Gdy Yatta napotka ten ciąg znaków, najpierw osobno przetłumaczy i zapisze w pamięci podręcznej nazwę przeciwnika, następnie jego typ, a podczas odczytywania tekstu użyje tych tłumaczeń i wstawi wszelkie liczby, które znajdzie dla punktów zdrowia, aby odczytać tłumaczenie.

## Dodatkowe uwagi

Jeśli zdecydujesz się na korzystanie z lokalnych modeli ollama, świetnym punktem wyjścia jest translategemma od Google. Jeśli posiadasz kartę graficzną z 12 GB pamięci VRAM, możesz użyć wariantu 12b, który zajmie około 8 GB pamięci i zapewni przyzwoite wyniki. W przypadku procesorów graficznych z mniejszą ilością pamięci RAM lub jeśli uznasz, że tłumaczenie jest zbyt wolne, wersja 4b zajmie około 3 GB pamięci, wciąż zapewniając bardzo dokładne tłumaczenie. Aby pobrać którykolwiek z tych modeli, po zainstalowaniu ollama otwórz wiersz poleceń i wpisz następujące polecenie:

```

ollama pull translategemma:12b


```

Zastępując 12b przez 4b, jeśli to tę wersję chcesz pobrać. Dodatkowo wprowadzenie pewnych zmian w ustawieniach Ollamy może poprawić wydajność. W szczególności użycie minimalnego rozmiaru kontekstu wynoszącego 4096 przyspieszy przetwarzanie i zmniejszy zużycie pamięci. YATTA nie zachowuje kontekstu rozmowy i dzieli dłuższe tłumaczenia co 4000 znaków, więc duży kontekst nie jest potrzebny.

Choć Google udostępnia listę obsługiwanych języków dla translategemma i zaleca podawanie w prompcie zarówno języka źródłowego, jak i docelowego, w praktyce możliwe jest nieokreślanie języka źródłowego i wpisanie auto, uzyskując dobry wynik, a także wpisanie języka docelowego, który nie jest oficjalnie obsługiwany. Niemniej jednak, określenie zarówno języka źródłowego, jak i docelowego może znacznie poprawić dokładność, nie tylko w przypadku modeli językowych. Opcje specyficzne dla aplikacji sprawdzają się w tym celu znakomicie.

Używanie modeli translategemma ma jedną wadę w porównaniu do usług takich jak DeepL czy modeli chmurowych – ma tendencję do pomijania tokenów podczas tłumaczenia dynamicznych ciągów znaków. Warto zmodyfikować domyślny prompt, aby podkreślić, że te tokeny powinny zostać zachowane, co powinno pomóc, ale nie jest to rozwiązanie idealne. Domyślny prompt YATTA dla Ollamy, niezależny od tego dostarczanego przez Google, już próbuje to robić. Jeśli token zostanie pominięty, YATTA ostrzeże Cię o tym, odczyta brakującą wartość i nie zapisze tłumaczenia w pamięci podręcznej. Jeśli zauważysz, że dzieje się to często w danym przypadku użycia, określ język źródłowy, spróbuj użyć innej usługi, utwórz więcej dynamicznych wpisów pamięci podręcznej lub wyłącz dzielenie liczb.

Na koniec omówienia tematu dzielenia liczb, jest to funkcja, którą najlepiej stosować w konkretnych aplikacjach lub grach. Do ogólnego tłumaczenia tekstów, takich jak posty w mediach społecznościowych, lepiej wysyłać tekst ze wszystkimi nienaruszonymi liczbami do usługi, aby zachować formatowanie takich rzeczy jak daty.

## Współtworzenie

Jeśli znalazłeś/aś błąd, chcesz zaproponować nową funkcję lub przetłumaczyć YATTA na swój własny język, Twoja pomoc jest niezwykle mile widziana. Najlepszym sposobem, aby to zrobić, jest otwarcie zgłoszenia (issue) w serwisie GitHub.

Na potrzeby rozwoju dodatku i tłumaczeń wykorzystywany jest część [szablonu dodatku NVDA](https://github.com/nvaccess/AddonTemplate). Aby zbudować pakiet dodatku lub wygenerować plik .pot do tłumaczenia, musisz posiadać zainstalowane pakiety: Python, SCons, gettext oraz pakiet Pythona `markdown`. Zależności Pythona, takie jak scons i markdown, można zainstalować za pomocą narzędzia `uv`, natomiast gettext można łatwo pobrać przy użyciu `winget`.



## Podziękowania

Projekt YATTA nie powstałby, gdyby nie dodatki do NVDA, które pojawiły się wcześniej i zainspirowały różne aspekty jego działania. Należą do nich JGT (Japanese Games Translator), [Instant Translate](https://github.com/nvdaaddons/instantTranslate) oraz [NVDA Translate](https://github.com/yplassiard/nvda-translate).

Chciałbym również podziękować moim testerom wersji pre-alpha – Oriolowi Gomezowi oraz Talonowi, którzy przekazali mi nieocenione uwagi i opinie.

## Zastrzeżenia

* Choć YATTA sama z siebie nie zbiera żadnych informacji, każdy tłumaczony tekst jest wysyłany do wybranej usługi tłumaczeniowej. Pamiętaj o polityce prywatności usługi, z której korzystasz, i nie tłumacz żadnych poufnych informacji.
* Ani YATTA, ani dostawcy usług nie mogą zagwarantować stu-procentowej dokładności tłumaczenia. Modele LLM mogą halucynować, nawet konwencjonalne usługi mogą dostarczać niepoprawne tłumaczenia. Jeśli tłumaczysz wrażliwe informacje, skonsultuj się z profesjonalnym tłumaczem.
* Duże modele językowe, w szczególności Google Gemini, zostały użyte do pomocy w rozwoju tego dodatku.