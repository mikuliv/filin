# Stateful episode processing

Stateful слой связывает последовательные observations в episodes и применяет
замороженную state policy. Решение зависит от causal order, а не от случайного
разбиения feature rows.

Подтверждённое поведение включает episode grouping, transitions, suppression и
passive disposition в лабораторном scope. Abstention и uncertainty сохраняются
как отдельные состояния и не подменяются правильным ответом.

Historical state policies относятся к своим candidate lineages. Current state
policy не изменялась в documentation maintenance.
