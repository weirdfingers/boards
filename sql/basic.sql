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
select storage_url
from generations
where status = 'completed';
--
-- for any generations where the storage_url is non-null and starts
-- with http://localhost:8088/api/storage/ make it start with http://localhost:8088/api/storage/
update generations
set storage_url = replace(
        storage_url,
        'http://localhost:8000/storage/',
        'http://localhost:8088/api/storage/'
    )
where storage_url is not null
    and storage_url like 'http://localhost:8000/storage/%';
---
select b.title,
    b.is_public,
    g.generator_name,
    g.artifact_type,
    g.storage_url,
    g.input_params
from generations g
    left join boards b on g.board_id = b.id;
