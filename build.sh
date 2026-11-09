#!/bin/bash
# Builds build/ValqLegends.jar. Needs a Java 21 JDK and the Paper API jar (set PAPER_API=path/to/paper-api-1.21.11-R0.1-SNAPSHOT.jar,
# optionally PAPER_LIBS=dir with its dependencies such as adventure/gson).
set -e
cd "$(dirname "$0")"
J="${JAVA_BIN:-C:/Users/adnan/AppData/Roaming/ElyPrismLauncher/java/java-runtime-delta/bin}"
LIBS="${PAPER_LIBS:-../estate-1211/libraries}"
API="${PAPER_API:-../estate-1211/versions/1.21.11/paper-1.21.11.jar}"
CP=$(find "$LIBS" -name "*.jar" | tr '\n' ';')"$API"
rm -rf build && mkdir -p build/classes
"$J/javac.exe" --release 21 -encoding UTF-8 -nowarn -cp "$CP" -d build/classes $(find src -name "*.java")
cp resources/*.yml build/classes/
(cd build/classes && "$J/jar.exe" cf ../ValqLegends.jar .)
ls -la build/ValqLegends.jar
