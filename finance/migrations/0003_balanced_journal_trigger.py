from django.db import migrations
from django.contrib.postgres.operations import BtreeGistExtension

class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_initial'),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION check_journal_entry_balance()
            RETURNS TRIGGER AS $$
            DECLARE
                total_debit NUMERIC(15, 2);
                total_credit NUMERIC(15, 2);
                target_entry_id BIGINT;
            BEGIN
                IF (TG_OP = 'DELETE') THEN
                    target_entry_id := OLD.ledger_entry_id;
                ELSE
                    target_entry_id := NEW.ledger_entry_id;
                END IF;

                SELECT COALESCE(SUM(debit), 0.00), COALESCE(SUM(credit), 0.00)
                INTO total_debit, total_credit
                FROM finance_generalledgerline
                WHERE ledger_entry_id = target_entry_id;

                IF total_debit <> total_credit THEN
                    RAISE EXCEPTION 'Database Constraint Violation: Unbalanced GeneralLedger entry ID % (Debit=%, Credit=%)',
                        target_entry_id, total_debit, total_credit;
                END IF;

                IF (TG_OP = 'DELETE') THEN
                    RETURN OLD;
                ELSE
                    RETURN NEW;
                END IF;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS trg_check_journal_balance ON finance_generalledgerline;

            CREATE CONSTRAINT TRIGGER trg_check_journal_balance
            AFTER INSERT OR UPDATE OR DELETE ON finance_generalledgerline
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW
            EXECUTE FUNCTION check_journal_entry_balance();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS trg_check_journal_balance ON finance_generalledgerline;
            DROP FUNCTION IF EXISTS check_journal_entry_balance();
            """
        )
    ]
