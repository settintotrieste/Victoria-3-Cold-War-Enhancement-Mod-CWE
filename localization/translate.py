import os
import time
import argparse
from tqdm import tqdm
from googletrans import Translator, LANGUAGES

# Please install "tqdm" and "googletrans" in advance.
# pip install tqdm googletrans

translator = Translator()
translatorCache = {}


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


def hasCommand(rawText) -> tuple[str, str]:
    # $foo$, [var], #foobar#! are commands which should not be translated
    isInCommand = False
    commandBrackets = {"$": "$", "[": "]", "#": "!"}
    commandPrefix = None
    for ch in rawText:
        if not isInCommand and ch in commandBrackets:
            # start of command
            isInCommand = True
            commandPrefix = ch
            continue
        elif isInCommand and ch == commandBrackets[commandPrefix]:
            # end of command
            return True
    return False


def translate(rawText, dstLang, srcLang="english") -> str:
    if rawText in translatorCache:
        return translatorCache[rawText]
    try:
        x = int(rawText.split(" ")[-1])
        rawText = " ".join(rawText.split(" ")[:-1])
        return translate(rawText, dstLang, srcLang) + " " + str(x)
    except:
        pass
    translatedText = rawText
    if hasAlphabets(rawText) and not hasCommand(rawText):
        while True:
            try:
                translatedText = translator.translate(rawText, dstLang, srcLang).text
                break
            except:
                print("Error occured. Waiting for 5 secs...")
                time.sleep(5)
    translatorCache[rawText] = translatedText
    return translatedText


def translateCWE(fileCommonName, dstLang, srcLang="english", overwriteFlag=False):
    inPath = os.path.join(srcLang, f"{fileCommonName}_{srcLang}.yml")
    outPath = os.path.join(dstLang, f"{fileCommonName}_{dstLang}.yml")
    if not overwriteFlag and os.path.exists(outPath):
        print(f"{outPath} exists. Skipping...")
        return

    print(f"Translating {inPath} ({srcLang}) -> {outPath} ({dstLang})")
    inFile = open(inPath, "r", encoding="utf-8")
    outFile = open(outPath, "w", encoding="utf-8")

    pbar = tqdm(total=getLineN(inPath))
    for line in inFile:
        pbar.update(1)
        if not hasAlphabets(line) or line.removeprefix(" ")[0] == "#":
            outFile.write(line)
            continue
        fields = line.split('"')
        if len(fields) == 3:
            rawtext = fields[1]
            translated = translate(rawtext, dstLang, srcLang)
            fields[1] = translated
        elif len(fields) == 1:
            fields[0] = fields[0].replace(f"l_{srcLang}", f"l_{dstLang}")
        newline = '"'.join(fields)
        outFile.write(newline)
    pbar.close()

    outFile.close()
    inFile.close()


if __name__ == "__main__":
    # print(list(LANGUAGES.values())) # Supported Languages

    # All you need to do is set these three variables below.
    fileCommonName = "0_general_l"  # If you want to translate 0_events_je_l_english.yml, set "0_events_je_l"
    srcLang = "english"  # Source Language
    dstLang = "japanese"  # Target Language

    translateCWE(fileCommonName, dstLang, srcLang)
