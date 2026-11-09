#!/bin/bash
# Builds build/ValqLegends.jar.
# Needs JAVA_HOME (a Java 21 JDK), PAPER_API (path to paper-api-1.21.11-R0.1-SNAPSHOT.jar) and optionally PAPER_LIBS
# (a folder with the jars Paper API depends on, e.g. adventure and gson).
set -e
cd "$(dirname "$0")"
: "${JAVA_HOME:?set JAVA_HOME to a Java 21 JDK}"
: "${PAPER_API:?set PAPER_API to the Paper API jar}"
CP="$PAPER_API"
if [ -n "$PAPER_LIBS" ]; then CP="$CP:$(find "$PAPER_LIBS" -name '*.jar' | tr '\n' ':')"; fi
rm -rf build && mkdir -p build/classes
"$JAVA_HOME/bin/javac" --release 21 -encoding UTF-8 -nowarn -cp "$CP" -d build/classes $(find src -name '*.java')
cp resources/*.yml build/classes/
(cd build/classes && "$JAVA_HOME/bin/jar" cf ../ValqLegends.jar .)
ls -la build/ValqLegends.jar
