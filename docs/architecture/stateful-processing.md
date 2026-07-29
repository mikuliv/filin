# Обработка эпизодов с состоянием

Stateful слой связывает последовательные observations в episodes и применяет
замороженную state policy. Решение зависит от causal order, а не от случайного
разбиения признак rows.

Подтверждённое поведение включает episode grouping, transitions, suppression и
passive disposition в лабораторном область применимости. Abstention и uncertainty сохраняются
как отдельные состояния и не подменяются правильным ответом.

исторический state policies относятся к своим candidate lineages. текущий state
policy не изменялась в documentation maintenance.
