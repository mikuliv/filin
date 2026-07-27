# Аудит Git-авторства

Проверяется `git log --all`: Author, Committer, `Co-authored-by`, merge/imported commits, первый и последний commit. Два email-алиаса `mikuliv` подтверждены как Руслан Покатилов; технический committer GitHub не трактуется как автор.

Актуальные числа находятся в `git-authorship.json`. Неизвестная identity даёт стабильный код `unknown_author`, `unknown_committer` или `unknown_coauthor` и блокирует готовность к распространению.

