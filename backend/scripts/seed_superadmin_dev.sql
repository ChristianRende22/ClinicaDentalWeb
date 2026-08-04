-- Siembra el superadmin en una base recien creada. SOLO PARA DESARROLLO.
--
-- Por que existe: el proyecto todavia no tiene script de seed (esta anotado como
-- pendiente de infraestructura del Modulo 1 en la pagina "Plannig" de Notion), asi
-- que cada vez que se recrea el volumen de MySQL hay que insertarlo a mano. Sin el
-- superadmin no se puede correr ninguna coleccion de Postman, porque todas arrancan
-- logueandose con el.
--
-- NO USAR EN PRODUCCION. La password esta hardcodeada y es publica: cualquiera que
-- lea este archivo puede entrar. Es aceptable en un entorno local y descartable.
--
-- Credenciales que crea:
--   usuario:  superadmin
--   password: Superadmin123
--
-- Son las mismas que traen por defecto las colecciones de Postman en sus variables
-- superadminUsername y superadminPassword.
--
-- Como correrlo, desde la raiz del repo y con los contenedores arriba:
--
--   Get-Content backend/scripts/seed_superadmin_dev.sql | docker compose exec -T db mysql -u root -p clinica_dental_web
--
-- (en bash/Linux seria:  docker compose exec -T db mysql -u root -p clinica_dental_web < backend/scripts/seed_superadmin_dev.sql)
--
-- Es idempotente: si el usuario ya existe, no hace nada.

INSERT INTO usuario (id_clinica, username, password_hash, rol, activo, debe_cambiar_password)
SELECT
    NULL,                    -- un superadmin no pertenece a ninguna clinica
    'superadmin',
    '$2b$12$UfdMhA/AOJTwrwslSZJY2umvJEZsivnmxGEEIvLeSN6ksYJPbNbf.',  -- bcrypt de 'Superadmin123'
    'superadmin',
    1,
    0                        -- 0 y no 1: no queremos que las colecciones tengan
                             -- que cambiar la password antes de poder operar
WHERE NOT EXISTS (
    SELECT 1 FROM usuario WHERE username = 'superadmin'
);

SELECT id_usuario, username, rol, activo, debe_cambiar_password, id_clinica
FROM usuario
WHERE username = 'superadmin';
