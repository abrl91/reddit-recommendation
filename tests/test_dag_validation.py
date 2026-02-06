import pytest

pytest.importorskip("airflow.models", reason="Full Airflow not installed")


class TestDagValidation:
    """Verify DAGs load and have correct structure."""

    def test_all_dags_load_without_errors(self) -> None:
        from airflow.models import DagBag

        dag_bag = DagBag(dag_folder="airflow/dags", include_examples=False)
        assert len(dag_bag.import_errors) == 0, f"Errors: {dag_bag.import_errors}"
        assert len(dag_bag.dags) == 18

    def test_source_dags_have_bronze_silver_tasks(self) -> None:
        from airflow.models import DagBag

        dag_bag = DagBag(dag_folder="airflow/dags", include_examples=False)

        source_dags = {
            dag_id: dag for dag_id, dag in dag_bag.dags.items() if "gold" not in dag_id
        }
        assert len(source_dags) == 16

        for dag_id, dag in source_dags.items():
            task_ids = [t.task_id for t in dag.tasks]
            assert "bronze" in task_ids, f"{dag_id} missing 'bronze' task"
            assert "silver" in task_ids, f"{dag_id} missing 'silver' task"

    def test_gold_dags_have_merge_task(self) -> None:
        from airflow.models import DagBag

        dag_bag = DagBag(dag_folder="airflow/dags", include_examples=False)

        gold_dags = {
            dag_id: dag for dag_id, dag in dag_bag.dags.items() if "gold" in dag_id
        }
        assert len(gold_dags) == 2

        for dag_id, dag in gold_dags.items():
            task_ids = [t.task_id for t in dag.tasks]
            assert "merge_to_gold" in task_ids, f"{dag_id} missing 'merge_to_gold'"

    def test_source_dag_bronze_runs_before_silver(self) -> None:
        """Bronze task should be upstream of silver (bronze >> silver)."""
        from airflow.models import DagBag

        dag_bag = DagBag(dag_folder="airflow/dags", include_examples=False)

        source_dags = {
            dag_id: dag for dag_id, dag in dag_bag.dags.items() if "gold" not in dag_id
        }
        for dag_id, dag in source_dags.items():
            task_map = {t.task_id: t for t in dag.tasks}
            silver_task = task_map["silver"]
            upstream_ids = [t.task_id for t in silver_task.upstream_list]
            assert "bronze" in upstream_ids, f"{dag_id}: silver should depend on bronze"
