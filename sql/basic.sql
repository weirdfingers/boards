-- list tables
select *
from information_schema.tables
where table_schema = 'public';
--
select *
from boards;
--
select * from users;
--
select * from tenants;
--
select * from board_members;
--
select * from generations;
