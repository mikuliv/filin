# Неопределённость и отказ от решения

## На уровне модели

Calibration и conformal set выражают ограниченную uncertainty в frozen evaluation
scope. State policy может отказаться от определённого класса. Это безопаснее, чем
принудительно выбирать label, но не гарантирует внешний coverage.

## На уровне реконструкции

Unknown interval boundaries, clock differences и missing evidence представлены
явными gaps. Они не превращаются в synthetic facts.

## На уровне гипотез

Несколько hypotheses могут иметь равную опору или быть incomparable. Матрица
показывает row-versus-column comparison, а не probability ranking. Результат
`equally_supported` не означает истинность обеих гипотез.

## На уровне оператора

Допустимый итог review — отсутствие окончательного определения и запрос нового
первичного материала. Такой итог не считается failure интерфейса.
