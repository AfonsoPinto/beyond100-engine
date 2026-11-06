#!/usr/bin/env bash
# Guarda ficheiros de estado no main sem nunca deixar marcas de conflito (<<<<<<<) nos JSON.
# Uso: bash save_state.sh "mensagem do commit" ficheiro1 ficheiro2 pasta1 ...
# Copia os ficheiros desta execução à parte, alinha com o main mais recente e repõe-nos por cima (esta execução ganha).
set -u
msg="$1"; shift
git config user.name "beyond100-bot"
git config user.email "bot@users.noreply.github.com"
keep=$(mktemp -d)
# o código vem do repositório público (beyond100-engine, em _engine/); o reset abaixo repunha o código antigo do privado,
# por isso volta-se sempre a pôr o código do motor por cima no fim (os passos seguintes do workflow correm com o código certo)
reengine() { if [ -d _engine ]; then tar -C _engine -cf - . | tar -xf -; fi; }
trap reengine EXIT
for p in "$@"; do
  if [ -e "$p" ]; then cp -r --parents "$p" "$keep"/; fi
done
for i in 1 2 3 4; do
  git fetch -q origin main || true
  git reset -q --hard origin/main
  cp -r "$keep"/. .
  for p in "$@"; do
    if [ -e "$p" ]; then git add -A -f "$p"; fi
  done
  if git diff --cached --quiet; then echo "Estado: nada para guardar."; exit 0; fi
  git commit -q -m "$msg"
  if git push -q origin HEAD:main; then echo "Estado guardado ($msg)."; exit 0; fi
  echo "Push recusado (tentativa $i), volto a tentar."
  sleep $((i * 5))
done
echo "Não consegui guardar o estado depois de 4 tentativas."
exit 1
