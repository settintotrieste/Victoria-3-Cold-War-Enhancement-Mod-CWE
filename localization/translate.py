import os
from tqdm import tqdm
from multiprocessing import Pool, freeze_support, RLock
import argostranslate.package
import argostranslate.translate

# Please install "tqdm" and "argostranslate" in advance.
# pip install tqdm argostranslate


def hasAlphabets(string):
    for ch in string:
        x = ord(ch)
        if ord("A") <= x and x <= ord("Z"):
            return True
        if ord("a") <= x and x <= ord("z"):
            return True
    return False


def getLineN(filepath):
    count = 0
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            count += 1
    return count


class CWE_Translator:
    def __init__(self, srcLang: str, dstLang: str):
        self.translatorCache = {}
        self.srcLang = srcLang
        self.dstLang = dstLang
        self.argosInit(srcLang, dstLang)
        langCodeDict = argostranslate.translate.get_installed_languages()
        self.srcLangCode = [
            x.code for x in langCodeDict if x.name.lower() == self.srcLang.lower()
        ][0]
        self.dstLangCode = [
            x.code for x in langCodeDict if x.name.lower() == self.dstLang.lower()
        ][0]

    def argosInit(self, srcLang, dstLang):
        print("Downloading Argos Package...")
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        try:
            package_to_install = next(
                filter(
                    lambda x: x.from_name.lower() == srcLang.lower()
                    and x.to_name.lower() == dstLang,
                    available_packages,
                )
            )
        except:
            raise ModuleNotFoundError(f"{srcLang} -> {dstLang} not supported.")
        argostranslate.package.install_from_path(package_to_install.download())

    def separateTextAndSymbols(self, rawText) -> tuple[str, str]:
        # $foo$, [var] and #foobar#! are symbols which should not be translated
        texts = [""]
        symbols = [""]
        isSymbol = False
        symbolBrackets = {"$": "$", "[": "]", "#": "!", "@": "!"}
        symbolPrefix = None
        for ch in rawText:
            if not isSymbol and ch in symbolBrackets:
                # start of command
                isSymbol = True
                symbolPrefix = ch
                texts.append("")
                symbols[-1] += ch
                continue
            elif isSymbol and ch == symbolBrackets[symbolPrefix]:
                # end of command
                isSymbol = False
                symbols[-1] += ch
                symbols.append("")
                continue
            if isSymbol:
                symbols[-1] += ch
            else:
                texts[-1] += ch
        return texts, symbols

    def mergeTextsAndSymbols(self, texts, symbols):
        result = ""
        while len(texts) > 0 or len(symbols) > 0:
            if len(texts) > 0:
                result += texts.pop(0)
            if len(symbols) > 0:
                result += symbols.pop(0)
        return result

    def translateLine(self, lineText) -> str:
        if lineText in self.translatorCache:
            return self.translatorCache[lineText]
        try:
            x = int(lineText.split(" ")[-1])
            lineText = " ".join(lineText.split(" ")[:-1])
            return self.translateLine(lineText) + " " + str(x)
        except:
            pass
        translatedText = lineText
        if hasAlphabets(lineText):
            texts, symbols = self.separateTextAndSymbols(lineText)
            if len(texts) > texts.count(""):
                newTexts = (
                    argostranslate.translate.translate(
                        " XXX ".join(texts), self.srcLangCode, self.dstLangCode
                    )
                    .replace("xxx", "XXX")
                    .split("XXX")
                )
                translatedText = self.mergeTextsAndSymbols(newTexts, symbols)
        self.translatorCache[lineText] = translatedText
        return translatedText

    def translateCWE(
        self,
        fileCommonName,
        overwriteFlag=False,
        position=0,
    ):
        inDir = self.srcLang
        outDir = self.dstLang
        os.makedirs(outDir, exist_ok=True)
        inPath = os.path.join(inDir, f"{fileCommonName}_{self.srcLang}.yml")
        outPath = os.path.join(outDir, f"{fileCommonName}_{self.dstLang}.yml")
        if not overwriteFlag and os.path.exists(outPath):
            print(f"{outPath} exists. Skipping...")
            return

        print(f"Translating {inPath} ({self.srcLang}) -> {outPath} ({self.dstLang})")
        inFile = open(inPath, "r", encoding="utf-8")
        outFile = open(outPath, "w", encoding="utf-8")

        pbar = tqdm(desc=fileCommonName, total=getLineN(inPath), position=position)
        for line in inFile:
            pbar.update(1)
            if not hasAlphabets(line) or line.removeprefix(" ")[0] == "#":
                outFile.write(line)
                continue
            fields = line.split('"')
            if len(fields) == 3:
                rawtext = fields[1]
                translated = self.translateLine(rawtext)
                fields[1] = translated
            elif len(fields) == 1:
                fields[0] = fields[0].replace(f"l_{self.srcLang}", f"l_{self.dstLang}")
            newline = '"'.join(fields)
            outFile.write(newline)
        pbar.close()

        outFile.close()
        inFile.close()

    def translateCWETask(self, input):
        position, fileCommonName = input
        self.translateCWE(fileCommonName, position=position)

    def translateCWEParalell(self, fileCommonNames):
        input = [
            (position, fileCommonNames[position])
            for position in range(len(fileCommonNames))
        ]
        freeze_support()
        with Pool(initializer=tqdm.set_lock, initargs=(RLock(),)) as p:
            p.map(self.translateCWETask, input)


if __name__ == "__main__":

    # All you need to do is set three variables below.
    fileCommonNames = [
        "0_buildings_l",  # If you want to translate 0_buildings_l_english.yml, set "0_buildings_l"
        "0_countries_l",
        "0_events_je_l",
        "0_general_l",
        "0_hub_names_l",
        "0_laws_l",
        "0_leaders_l",
        "0_states_l",
        "0_techs_l",
    ]
    srcLang = "english"  # Source Language
    dstLang = "german"  # Target Language

    ct = CWE_Translator(srcLang, dstLang)
    ct.translateCWEParalell(fileCommonNames)
