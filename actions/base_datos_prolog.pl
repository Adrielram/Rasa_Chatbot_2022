materia(6111,"Introduccion a la programacion I",1,1).
materia(6112,"Analisis Matematico I",1,1).
materia(6113,"Algebra I",1,1).
materia(6114,"Quimica",1,1).
materia(6121,"Ciencias de la Computacion I",1,2).
materia(6122,"Introduccion a la Programacion II",1,2).
materia(6123,"Algebra Lineal",1,2).
materia(6124,"Fisica General",1,2).
materia(6125,"Matematica Discreta",1,2).
materia(6211,"Ciencias de la Computacion II",2,1).
materia(6221,"Analisis y disenio de algoritmos II",2,2).
materia(6225,"Ingles",2,2).
materia(6224,"Eletronica Digital",2,2).
materia(6223,"Probabilidad y Estadistica",2,2).
materia(6222,"Comunicacion de Datos I",2,2).
materia(6321,"Programacion exploratoria",3,2).
correlativas(6111,[]).
correlativas(6112,[]).
correlativas(6113,[]).
correlativas(6114,[]).
correlativas(6121,[]).
correlativas(6122,[6111]).
correlativas(6123,[6113]).
correlativas(6124,[6112]).
correlativas(6125,[6113]).
correlativas(6211,[6121,6122,6125]).
materias_de(X):- materia(_,Y,X,_), write(Y),nl,fail.
materias_de(_).
materias(C,Z,Y,X):- materia(C,Z,Y,X),fail.
materias_con_una_correlativa:- correlativas(C,[_|[]]),materia(C,X,_,_),writeln(X),fail.
materias_con_una_correlativa.
muestra_lista([]):- write('No tiene correlativas').
muestra_lista([H|[]]):- write(' '),materia(H,X,_,_),write(X),write('.').
muestra_lista([H|L]):- not(L = []),materia(H,X,_,_),write(X),write(', '),muestra_lista(L),fail.
muestra_correlativas(C):- correlativas(C,L),muestra_lista(L).
muestra_materias:- materia(Code,X,Curso,Cuatri),write('Curso:'),write(Curso),
		   write(' Cuatri:'),write(Cuatri),write(' Nom:'),write(X),
		   write(' Correlativa/s:'),muestra_correlativas(Code),nl,fail.
plan_is:- writeln('Plan de Ingenieria en Sistemas:'),muestra_materias.
plan_is.
cursando([6221,6222,6223,6224,6225,6321]).
