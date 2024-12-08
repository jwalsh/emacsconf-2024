#!/bin/bash

# Create or overwrite summaries.org with a header
cat > summaries.org << EOL
#+TITLE: EmacsConf 2024 Talk Summaries
#+DATE: $(date +%Y-%m-%d)

EOL

# Find all org files and append their content
for file in summaries/*.org; do
 # Append content but strip the Meta section
 sed '/^** Meta/,$d' "$file" >> summaries.org
 echo -e "\n\n- [[${file}][Source]]\n" >> summaries.org
done

echo "Generated summaries.org"
