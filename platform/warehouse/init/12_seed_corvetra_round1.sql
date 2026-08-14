BEGIN;

SELECT pg_advisory_xact_lock(
    hashtextextended('open-dataops-platform:canonical-seed:round1:v1', 0)
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6'::uuid, 'production'),
            ('00b7a432-4e39-544a-9fdf-c990442446be'::uuid, 'development')
        ) AS expected(id, key)
        JOIN metadata.environments actual
          ON actual.environment_id = expected.id OR actual.environment_key = expected.key
        WHERE actual.environment_id <> expected.id OR actual.environment_key <> expected.key
    ) THEN
        RAISE EXCEPTION 'Canonical environment identity/key collision';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('b8548a45-da0b-5539-9886-6f25e572e3e7'::uuid, 'events-kafka'),
            ('c6f05a23-c1f5-5117-ab9a-ba0346641e56'::uuid, 'billing-postgres'),
            ('1820bdc4-b5e0-5abc-bc39-abd2d0e04573'::uuid, 'analytics-warehouse'),
            ('cbca18a9-9fda-5947-a9f4-144c98e969d0'::uuid, 'customer-sqlserver')
        ) AS expected(id, key)
        JOIN metadata.data_sources actual
          ON actual.data_source_id = expected.id OR actual.source_key = expected.key
        WHERE actual.data_source_id <> expected.id OR actual.source_key <> expected.key
    ) THEN
        RAISE EXCEPTION 'Canonical data-source identity/key collision';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('38cfb7c0-9a96-5ce2-9631-8e5632fa6142'::uuid, 'events-processing'),
            ('b60113e8-c326-578c-a609-aea6ef66923b'::uuid, 'billing-reconciliation'),
            ('cf12532b-201d-5659-a2c4-a2110a81dba4'::uuid, 'customer-ingestion')
        ) AS expected(id, key)
        JOIN metadata.pipelines actual
          ON actual.pipeline_id = expected.id OR actual.pipeline_key = expected.key
        WHERE actual.pipeline_id <> expected.id OR actual.pipeline_key <> expected.key
    ) THEN
        RAISE EXCEPTION 'Canonical pipeline identity/key collision';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('e408fd55-1a14-5b44-9eb5-8eb6b97b8d62'::uuid, 'order-id-unique'),
            ('9e7c9eca-c81d-59de-b5a3-9df44034bb0d'::uuid, 'payment-status-accepted-values'),
            ('d4c699e7-e974-5ca4-9473-08a2579f5bf1'::uuid, 'customer-id-not-null'),
            ('4e119ba2-4280-5026-ae6e-d2be88351008'::uuid, 'customer-email-null-rate')
        ) AS expected(id, key)
        JOIN metadata.validation_checks actual
          ON actual.validation_check_id = expected.id OR actual.check_key = expected.key
        WHERE actual.validation_check_id <> expected.id OR actual.check_key <> expected.key
    ) THEN
        RAISE EXCEPTION 'Canonical validation-check identity/key collision';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('fe6dc079-ef9e-52e6-b819-5252c8f4b5b8'::uuid, 'ALT-1042'),
            ('d2687a77-1fec-5617-90eb-78f9ef3f3f74'::uuid, 'ALT-1040'),
            ('37050c5b-df7f-5164-a33a-721c06e764eb'::uuid, 'ALT-1037')
        ) AS expected(id, key)
        JOIN metadata.operational_alerts actual
          ON actual.alert_id = expected.id OR actual.alert_key = expected.key
        WHERE actual.alert_id <> expected.id OR actual.alert_key <> expected.key
    ) THEN
        RAISE EXCEPTION 'Canonical operational-alert identity/key collision';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('8420c60b-0951-5442-b172-527c704b90ea'::uuid, 'evt-001'),
            ('4e873f19-8047-5116-88ef-75f3b735e8d1'::uuid, 'evt-002'),
            ('12e16d84-fa89-54dc-99af-280ec51861fb'::uuid, 'evt-003'),
            ('6155752e-d808-5f25-8207-80777f3f3f27'::uuid, 'evt-004'),
            ('31bfb8b6-002b-57a0-a774-150be8a9e196'::uuid, 'evt-005'),
            ('c617cebf-4040-592b-8f5f-66bdd76798e9'::uuid, 'evt-007')
        ) AS expected(id, key)
        JOIN metadata.technical_events actual
          ON actual.technical_event_id = expected.id OR actual.event_key = expected.key
        WHERE actual.technical_event_id <> expected.id OR actual.event_key <> expected.key
    ) THEN
        RAISE EXCEPTION 'Canonical technical-event identity/key collision';
    END IF;
END $$;

INSERT INTO metadata.environments
    (environment_id, environment_key, environment_name)
VALUES
    ('acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', 'production', 'Production'),
    ('00b7a432-4e39-544a-9fdf-c990442446be', 'development', 'Development')
ON CONFLICT (environment_key) DO NOTHING;

INSERT INTO metadata.data_sources
    (data_source_id, source_key, source_name, source_type, environment_id, operational_status)
VALUES
    ('b8548a45-da0b-5539-9886-6f25e572e3e7', 'events-kafka', 'Events Kafka', 'KAFKA',
     'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', 'DISCONNECTED'),
    ('c6f05a23-c1f5-5117-ab9a-ba0346641e56', 'billing-postgres', 'Billing PostgreSQL', 'POSTGRESQL',
     'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', 'WARNING'),
    ('1820bdc4-b5e0-5abc-bc39-abd2d0e04573', 'analytics-warehouse', 'Production Warehouse', 'SNOWFLAKE',
     'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', 'HEALTHY'),
    ('cbca18a9-9fda-5947-a9f4-144c98e969d0', 'customer-sqlserver', 'Legacy SQL Server', 'SQL_SERVER',
     '00b7a432-4e39-544a-9fdf-c990442446be', 'DISABLED')
ON CONFLICT (source_key) DO NOTHING;

INSERT INTO metadata.pipelines
    (pipeline_id, pipeline_key, pipeline_name, environment_id, data_source_id,
     airflow_dag_id, is_enabled)
VALUES
    ('38cfb7c0-9a96-5ce2-9631-8e5632fa6142', 'events-processing', 'Events Processing',
     'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', 'b8548a45-da0b-5539-9886-6f25e572e3e7',
     'corvetra_demo__events_processing', TRUE),
    ('b60113e8-c326-578c-a609-aea6ef66923b', 'billing-reconciliation', 'Billing Reconciliation',
     'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', 'c6f05a23-c1f5-5117-ab9a-ba0346641e56',
     'corvetra_demo__billing_reconciliation', TRUE),
    ('cf12532b-201d-5659-a2c4-a2110a81dba4', 'customer-ingestion', 'Customer Ingestion',
     'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6', '1820bdc4-b5e0-5abc-bc39-abd2d0e04573',
     'corvetra_demo__customer_ingestion', TRUE)
ON CONFLICT (pipeline_key) DO NOTHING;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d'::uuid, 'run_01J94EVT18',
             'corvetra_demo__events_processing', 'corvetra_seed__run_01J94EVT18'),
            ('3807f462-fee5-520a-8b10-8a1afa657fc2'::uuid, 'run_01J97BIL02',
             'corvetra_demo__billing_reconciliation', 'corvetra_seed__run_01J97BIL02'),
            ('572537ed-21fa-51a9-98fd-a3ff7d046f3b'::uuid, 'run_01J92CING8',
             'corvetra_demo__customer_ingestion', 'corvetra_seed__run_01J92CING8'),
            ('3407e7be-2e8f-5b90-8d13-6b8eb428050d'::uuid, 'run_01J92CVAL9',
             'corvetra_demo__customer_ingestion', 'corvetra_seed__run_01J92CVAL9'),
            ('b0d4a95a-3fc1-585c-a21a-f4572628cfc5'::uuid, 'run_01JA7OLD40',
             'corvetra_demo__customer_ingestion', 'corvetra_seed__run_01JA7OLD40')
        ) AS expected(id, key, dag, airflow_run)
        JOIN metadata.pipeline_runs actual
          ON actual.pipeline_run_id = expected.id
          OR actual.corvetra_run_id = expected.key
          OR (actual.dag_id = expected.dag AND actual.airflow_run_id = expected.airflow_run)
        WHERE actual.pipeline_run_id <> expected.id
           OR actual.corvetra_run_id IS DISTINCT FROM expected.key
           OR actual.dag_id <> expected.dag
           OR actual.airflow_run_id <> expected.airflow_run
    ) THEN
        RAISE EXCEPTION 'Canonical pipeline-run identity/key/Airflow collision';
    END IF;
END $$;

INSERT INTO metadata.pipeline_runs
    (pipeline_run_id, dag_id, airflow_run_id, started_at, completed_at, run_status,
     corvetra_run_id, pipeline_id, stage_name, platform_code, vendor_code, rule_code)
VALUES
    ('7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
     'corvetra_demo__events_processing', 'corvetra_seed__run_01J94EVT18',
     '2026-08-10T14:41:03Z', '2026-08-10T14:42:38.412Z', 'FAILED',
     'run_01J94EVT18', '38cfb7c0-9a96-5ce2-9631-8e5632fa6142', 'EXTRACT',
     'PIPELINE_EXECUTION_FAILED', 'SASL_AUTHENTICATION_FAILED', NULL),
    ('3807f462-fee5-520a-8b10-8a1afa657fc2',
     'corvetra_demo__billing_reconciliation', 'corvetra_seed__run_01J97BIL02',
     '2026-08-10T13:28:00Z', '2026-08-10T13:36:42Z', 'FAILED',
     'run_01J97BIL02', 'b60113e8-c326-578c-a609-aea6ef66923b', 'VALIDATE',
     'VALIDATION_CHECK_FAILED', NULL, 'CHECK_UNIQUENESS_VIOLATION'),
    ('572537ed-21fa-51a9-98fd-a3ff7d046f3b',
     'corvetra_demo__customer_ingestion', 'corvetra_seed__run_01J92CING8',
     '2026-08-10T14:32:00Z', '2026-08-10T14:34:14Z', 'SUCCESS',
     'run_01J92CING8', 'cf12532b-201d-5659-a2c4-a2110a81dba4', 'LOAD',
     'RUN_COMPLETED', NULL, NULL),
    ('3407e7be-2e8f-5b90-8d13-6b8eb428050d',
     'corvetra_demo__customer_ingestion', 'corvetra_seed__run_01J92CVAL9',
     '2026-08-10T14:05:00Z', '2026-08-10T14:07:20Z', 'SUCCESS',
     'run_01J92CVAL9', 'cf12532b-201d-5659-a2c4-a2110a81dba4', 'LOAD',
     'RUN_COMPLETED_WITH_WARNINGS', NULL, 'CHECK_NULL_RATE_THRESHOLD'),
    ('b0d4a95a-3fc1-585c-a21a-f4572628cfc5',
     'corvetra_demo__customer_ingestion', 'corvetra_seed__run_01JA7OLD40',
     '2026-08-09T19:14:00Z', '2026-08-09T19:14:18Z', 'FAILED',
     'run_01JA7OLD40', 'cf12532b-201d-5659-a2c4-a2110a81dba4', 'EXTRACT',
     'PIPELINE_EXECUTION_FAILED', 'SNOWFLAKE_CONNECTION_RESET', NULL)
ON CONFLICT (pipeline_run_id) DO UPDATE SET
    dag_id = EXCLUDED.dag_id,
    airflow_run_id = EXCLUDED.airflow_run_id,
    started_at = EXCLUDED.started_at,
    completed_at = EXCLUDED.completed_at,
    run_status = EXCLUDED.run_status,
    corvetra_run_id = EXCLUDED.corvetra_run_id,
    pipeline_id = EXCLUDED.pipeline_id,
    stage_name = EXCLUDED.stage_name,
    platform_code = EXCLUDED.platform_code,
    vendor_code = EXCLUDED.vendor_code,
    rule_code = EXCLUDED.rule_code;

INSERT INTO metadata.validation_checks
    (validation_check_id, check_key, pipeline_id, check_name, check_type,
     dataset_name, column_name, default_severity, is_enabled)
VALUES
    ('e408fd55-1a14-5b44-9eb5-8eb6b97b8d62', 'order-id-unique',
     'b60113e8-c326-578c-a609-aea6ef66923b', 'Order ID unique', 'UNIQUE',
     'orders', 'order_id', 'BLOCKING', TRUE),
    ('9e7c9eca-c81d-59de-b5a3-9df44034bb0d', 'payment-status-accepted-values',
     'b60113e8-c326-578c-a609-aea6ef66923b', 'Payment status accepted values', 'ACCEPTED_VALUES',
     'payments', 'payment_status', 'WARNING', TRUE),
    ('d4c699e7-e974-5ca4-9473-08a2579f5bf1', 'customer-id-not-null',
     'cf12532b-201d-5659-a2c4-a2110a81dba4', 'Customer ID not null', 'NOT_NULL',
     'customers', 'customer_id', 'BLOCKING', TRUE),
    ('4e119ba2-4280-5026-ae6e-d2be88351008', 'customer-email-null-rate',
     'cf12532b-201d-5659-a2c4-a2110a81dba4', 'Customer email null rate', 'NOT_NULL',
     'customers', 'customer_email', 'WARNING', TRUE)
ON CONFLICT (check_key) DO NOTHING;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('41801d5b-ae43-5da5-8d11-6934430eeaeb'::uuid,
             '3807f462-fee5-520a-8b10-8a1afa657fc2'::uuid,
             'e408fd55-1a14-5b44-9eb5-8eb6b97b8d62'::uuid),
            ('e69d7271-b85e-5159-a820-c96f90a5db2f'::uuid,
             '3807f462-fee5-520a-8b10-8a1afa657fc2'::uuid,
             '9e7c9eca-c81d-59de-b5a3-9df44034bb0d'::uuid),
            ('0f871e27-e5e8-5a61-9539-e7cb1ae61249'::uuid,
             '572537ed-21fa-51a9-98fd-a3ff7d046f3b'::uuid,
             'd4c699e7-e974-5ca4-9473-08a2579f5bf1'::uuid),
            ('72440277-d802-5294-847f-f6c0753dd7b7'::uuid,
             '3407e7be-2e8f-5b90-8d13-6b8eb428050d'::uuid,
             '4e119ba2-4280-5026-ae6e-d2be88351008'::uuid)
        ) AS expected(id, run_id, check_id)
        JOIN metadata.validation_executions actual
          ON actual.validation_execution_id = expected.id
          OR (actual.pipeline_run_id = expected.run_id
              AND actual.validation_check_id = expected.check_id)
        WHERE actual.validation_execution_id <> expected.id
           OR actual.pipeline_run_id <> expected.run_id
           OR actual.validation_check_id <> expected.check_id
    ) THEN
        RAISE EXCEPTION 'Canonical validation-execution identity/run/check collision';
    END IF;
END $$;

INSERT INTO metadata.validation_executions
    (validation_execution_id, pipeline_run_id, validation_check_id, dbt_result_id,
     stage_name, result_status, effective_severity, platform_code, rule_code,
     vendor_code, actual_value, expected_value, result_message, evaluated_at)
VALUES
    ('41801d5b-ae43-5da5-8d11-6934430eeaeb',
     '3807f462-fee5-520a-8b10-8a1afa657fc2', 'e408fd55-1a14-5b44-9eb5-8eb6b97b8d62', NULL,
     'VALIDATE', 'FAILED', 'BLOCKING', 'VALIDATION_CHECK_FAILED',
     'CHECK_UNIQUENESS_VIOLATION', NULL, '318 duplicates', '0 duplicates',
     '318 duplicate order_id values were detected.', '2026-08-10T13:36:42Z'),
    ('e69d7271-b85e-5159-a820-c96f90a5db2f',
     '3807f462-fee5-520a-8b10-8a1afa657fc2', '9e7c9eca-c81d-59de-b5a3-9df44034bb0d', NULL,
     'VALIDATE', 'PASSED', 'WARNING', 'VALIDATION_CHECK_PASSED',
     NULL, NULL, '0 invalid', '0 invalid',
     'All payment_status values matched the accepted set.', '2026-08-10T13:36:42Z'),
    ('0f871e27-e5e8-5a61-9539-e7cb1ae61249',
     '572537ed-21fa-51a9-98fd-a3ff7d046f3b', 'd4c699e7-e974-5ca4-9473-08a2579f5bf1', NULL,
     'VALIDATE', 'PASSED', 'BLOCKING', 'VALIDATION_CHECK_PASSED',
     NULL, NULL, '0 nulls', '0 nulls',
     'No null values were detected in customer_id.', '2026-08-10T14:33:48Z'),
    ('72440277-d802-5294-847f-f6c0753dd7b7',
     '3407e7be-2e8f-5b90-8d13-6b8eb428050d', '4e119ba2-4280-5026-ae6e-d2be88351008', NULL,
     'VALIDATE', 'FAILED', 'WARNING', 'VALIDATION_CHECK_FAILED',
     'CHECK_NULL_RATE_THRESHOLD', NULL, '3.7% null', '< 2% null',
     'The percentage of null values in customer_email exceeded the configured threshold.',
     '2026-08-10T14:06:45Z')
ON CONFLICT (validation_execution_id) DO UPDATE SET
    pipeline_run_id = EXCLUDED.pipeline_run_id,
    validation_check_id = EXCLUDED.validation_check_id,
    dbt_result_id = EXCLUDED.dbt_result_id,
    stage_name = EXCLUDED.stage_name,
    result_status = EXCLUDED.result_status,
    effective_severity = EXCLUDED.effective_severity,
    platform_code = EXCLUDED.platform_code,
    rule_code = EXCLUDED.rule_code,
    vendor_code = EXCLUDED.vendor_code,
    actual_value = EXCLUDED.actual_value,
    expected_value = EXCLUDED.expected_value,
    result_message = EXCLUDED.result_message,
    evaluated_at = EXCLUDED.evaluated_at;

INSERT INTO metadata.operational_alerts
    (alert_id, alert_key, pipeline_run_id, validation_execution_id, alert_title,
     severity, alert_status, platform_code, vendor_code, rule_code, alert_message,
     detected_at, last_seen_at, acknowledged_at, resolved_at)
VALUES
    ('fe6dc079-ef9e-52e6-b819-5252c8f4b5b8', 'ALT-1042',
     '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d', NULL,
     'Pipeline execution failing', 'CRITICAL', 'OPEN', 'PIPELINE_EXECUTION_FAILED',
     'SASL_AUTHENTICATION_FAILED', NULL,
     'Events Kafka rejected the configured SASL credentials during Extract.',
     '2026-08-10T14:42:38.412Z', '2026-08-10T14:43:00Z', NULL, NULL),
    ('d2687a77-1fec-5617-90eb-78f9ef3f3f74', 'ALT-1040',
     '3807f462-fee5-520a-8b10-8a1afa657fc2', '41801d5b-ae43-5da5-8d11-6934430eeaeb',
     'Order ID unique failed', 'WARNING', 'OPEN', 'VALIDATION_CHECK_FAILED',
     NULL, 'CHECK_UNIQUENESS_VIOLATION',
     'The blocking Order ID unique check found 318 duplicates; expected 0 duplicates.',
     '2026-08-10T13:36:42Z', '2026-08-10T13:36:42Z', NULL, NULL),
    ('37050c5b-df7f-5164-a33a-721c06e764eb', 'ALT-1037',
     'b0d4a95a-3fc1-585c-a21a-f4572628cfc5', NULL,
     'Extraction connection interrupted', 'WARNING', 'RESOLVED', 'PIPELINE_EXECUTION_FAILED',
     'SNOWFLAKE_CONNECTION_RESET', NULL,
     'Production Warehouse reset the connection during a historical extraction run.',
     '2026-08-09T19:14:18Z', '2026-08-09T19:14:18Z', NULL, '2026-08-09T19:34:00Z')
ON CONFLICT (alert_key) DO NOTHING;

INSERT INTO metadata.technical_events
    (technical_event_id, event_key, occurred_at, event_level, environment_id,
     pipeline_id, pipeline_run_id, data_source_id, alert_id, validation_execution_id,
     stage_name, platform_code, vendor_code, rule_code, event_message, event_details)
VALUES
    ('31bfb8b6-002b-57a0-a774-150be8a9e196', 'evt-005',
     '2026-08-10T14:41:03.110Z', 'DEBUG', 'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6',
     '38cfb7c0-9a96-5ce2-9631-8e5632fa6142', '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
     'b8548a45-da0b-5539-9886-6f25e572e3e7', NULL, NULL, 'EXTRACT', NULL, NULL, NULL,
     'Extract stage started for the events topic.',
     jsonb_build_object('topic', 'product-events', 'partition_count', 12, 'component', 'extractor')),
    ('6155752e-d808-5f25-8207-80777f3f3f27', 'evt-004',
     '2026-08-10T14:42:35.204Z', 'INFO', 'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6',
     '38cfb7c0-9a96-5ce2-9631-8e5632fa6142', '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
     'b8548a45-da0b-5539-9886-6f25e572e3e7', NULL, NULL, 'EXTRACT', NULL, NULL, NULL,
     'Extracting events topic.', jsonb_build_object('table', 'events topic', 'batch_size', 5000)),
    ('12e16d84-fa89-54dc-99af-280ec51861fb', 'evt-003',
     '2026-08-10T14:42:36.125Z', 'WARNING', 'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6',
     '38cfb7c0-9a96-5ce2-9631-8e5632fa6142', '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
     'b8548a45-da0b-5539-9886-6f25e572e3e7', NULL, NULL, 'EXTRACT',
     'SOURCE_CONNECTION_RETRY_FAILED', NULL, NULL, 'Connection retry 2/3 failed.',
     jsonb_build_object('attempt', 2, 'max_attempts', 3, 'backoff_ms', 2000)),
    ('4e873f19-8047-5116-88ef-75f3b735e8d1', 'evt-002',
     '2026-08-10T14:42:37.981Z', 'WARNING', 'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6',
     '38cfb7c0-9a96-5ce2-9631-8e5632fa6142', '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
     'b8548a45-da0b-5539-9886-6f25e572e3e7', NULL, NULL, 'EXTRACT',
     'SOURCE_CONNECTION_RETRY_FAILED', NULL, NULL, 'Connection retry 3/3 failed.',
     jsonb_build_object('attempt', 3, 'max_attempts', 3, 'backoff_ms', 4000, 'component', 'extractor')),
    ('8420c60b-0951-5442-b172-527c704b90ea', 'evt-001',
     '2026-08-10T14:42:38.412Z', 'ERROR', 'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6',
     '38cfb7c0-9a96-5ce2-9631-8e5632fa6142', '7214b5a0-8e87-52c2-a5e0-0cc69a5b8a2d',
     'b8548a45-da0b-5539-9886-6f25e572e3e7', 'fe6dc079-ef9e-52e6-b819-5252c8f4b5b8', NULL,
     'EXTRACT', 'PIPELINE_EXECUTION_FAILED', 'SASL_AUTHENTICATION_FAILED', NULL,
     'Events Kafka rejected the configured SASL credentials during extraction.',
     jsonb_build_object(
         'attempt', 3, 'max_attempts', 3, 'broker', 'events-01.internal:9093',
         'mechanism', 'SCRAM-SHA-512', 'component', 'extractor', 'credential', '[REDACTED]',
         'interpretation', 'The extraction stopped after Events Kafka rejected all three authentication attempts.',
         'stack_trace', E'AuthenticationError: Events Kafka rejected SASL credentials\n    at KafkaConnector.connect (connector.ts:91:13)\n    at async ExtractStage.execute (stage.ts:72:9)\nCaused by: SASL_AUTHENTICATION_FAILED'
     )),
    ('c617cebf-4040-592b-8f5f-66bdd76798e9', 'evt-007',
     '2026-08-10T13:36:42Z', 'ERROR', 'acd26c1f-ee5d-5f6c-ac9f-19070baf3dc6',
     'b60113e8-c326-578c-a609-aea6ef66923b', '3807f462-fee5-520a-8b10-8a1afa657fc2',
     'c6f05a23-c1f5-5117-ab9a-ba0346641e56', 'd2687a77-1fec-5617-90eb-78f9ef3f3f74',
     '41801d5b-ae43-5da5-8d11-6934430eeaeb', 'VALIDATE', 'VALIDATION_CHECK_FAILED',
     NULL, 'CHECK_UNIQUENESS_VIOLATION',
     'Order ID unique found 318 duplicate order_id values; expected 0 duplicates. The blocking validation stopped execution before Load.',
     jsonb_build_object(
         'check', 'unique', 'field', 'order_id', 'observed', '318 duplicates',
         'threshold', '0 duplicates', 'evaluated_records', 118204
     ))
ON CONFLICT (technical_event_id) DO UPDATE SET
    event_key = EXCLUDED.event_key,
    occurred_at = EXCLUDED.occurred_at,
    event_level = EXCLUDED.event_level,
    environment_id = EXCLUDED.environment_id,
    pipeline_id = EXCLUDED.pipeline_id,
    pipeline_run_id = EXCLUDED.pipeline_run_id,
    data_source_id = EXCLUDED.data_source_id,
    alert_id = EXCLUDED.alert_id,
    validation_execution_id = EXCLUDED.validation_execution_id,
    stage_name = EXCLUDED.stage_name,
    platform_code = EXCLUDED.platform_code,
    vendor_code = EXCLUDED.vendor_code,
    rule_code = EXCLUDED.rule_code,
    event_message = EXCLUDED.event_message,
    event_details = EXCLUDED.event_details;

COMMIT;
