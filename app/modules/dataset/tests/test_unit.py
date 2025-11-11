import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, url_for
from datetime import datetime, timezone
from app.modules.dataset.services import DataSetService
from app.modules.dataset.repositories import DSDownloadRecordRepository
from app.modules.dataset.models import DataSet
from app.modules.dataset.services import DSDownloadRecordService
from app.modules.badge.routes import badge_bp, get_dataset, make_segment

FIXED_TIME = datetime(2025, 12, 1, 15, 0, 0, tzinfo=timezone.utc)

@pytest.fixture
def mock_dsdownloadrecord_repository():
    repository = MagicMock(spec=DSDownloadRecordRepository)
    mock_dataset = MagicMock(spec=DataSet)
    repository.top_3_dowloaded_datasets_per_week.return_value = [mock_dataset] * 3
    return repository


@pytest.fixture
def dataset_service(mock_dsdownloadrecord_repository):
    service = DataSetService()
    service.dsdownloadrecord_repository = mock_dsdownloadrecord_repository
    return service

@pytest.fixture
def download_service(mock_dsdownloadrecord_repository):
    service = DSDownloadRecordService()
    service.repository = mock_dsdownloadrecord_repository
    return service

#badge
@pytest.fixture
def app():
    app = Flask(__name__)
    app.register_blueprint(badge_bp)
    app.config['TESTING'] = True
    return app

#badge
@pytest.fixture
def client(app):
    return app.test_client()

#badge
@pytest.fixture
def mock_dataset():
    ds_mock = {
        "title": "Test Dataset",
        "downloads": 42,
        "doi": "10.1234/testdoi",
        "url": "http://example.com/dataset"
    }
    return ds_mock

def test_download_counter_registered_for_authenticated_user(
    download_service,
    mock_dsdownloadrecord_repository
):
    test_user_id = 99
    test_dataset_id = 1
    test_cookie = "auth-cookie-123"
    
    download_service.create(
        user_id=test_user_id,
        dataset_id=test_dataset_id,
        download_date=FIXED_TIME,
        download_cookie=test_cookie,
    )

    mock_dsdownloadrecord_repository.create.assert_called_once_with(
        user_id=test_user_id,
        dataset_id=test_dataset_id,
        download_date=FIXED_TIME,
        download_cookie=test_cookie,
    )

def test_download_counter_registered_for_unauthenticated_user(
    download_service,
    mock_dsdownloadrecord_repository
):
    test_dataset_id = 2
    test_cookie = "anon-cookie-456"

    download_service.create(
        user_id=None, 
        dataset_id=test_dataset_id,
        download_date=FIXED_TIME, 
        download_cookie=test_cookie,
    )

    mock_dsdownloadrecord_repository.create.assert_called_once()
    args, kwargs = mock_dsdownloadrecord_repository.create.call_args
    assert kwargs.get('user_id') is None
    assert kwargs.get('dataset_id') == test_dataset_id
    assert kwargs.get('download_cookie') == test_cookie

def test_multiple_downloads_from_same_user_are_registered(
    download_service,
    mock_dsdownloadrecord_repository
):
    test_user_id = 77
    test_dataset_id = 5
    test_cookie = "repetitive-cookie"
    
    download_service.create(
        user_id=test_user_id,
        dataset_id=test_dataset_id,
        download_date=FIXED_TIME,
        download_cookie=test_cookie,
    )
    
    download_service.create(
        user_id=test_user_id,
        dataset_id=test_dataset_id,
        download_date=FIXED_TIME,
        download_cookie=test_cookie,
    )

    assert mock_dsdownloadrecord_repository.create.call_count == 2
    
    mock_dsdownloadrecord_repository.create.assert_any_call(
        user_id=test_user_id,
        dataset_id=test_dataset_id,
        download_date=FIXED_TIME,
        download_cookie=test_cookie,
    )

def test_download_counter_raises_error_with_null_dataset_id(
    download_service,
    mock_dsdownloadrecord_repository
):
    mock_dsdownloadrecord_repository.create.side_effect = Exception("IntegrityError: dataset_id is required")

    with pytest.raises(Exception, match="IntegrityError: dataset_id is required"):
        download_service.create(
            user_id=1,
            dataset_id=None,
            download_date=FIXED_TIME,
            download_cookie="null-id-cookie",
        )
        
    mock_dsdownloadrecord_repository.create.assert_called_once()

def test_download_counter_raises_error_with_null_cookie(
    download_service,
    mock_dsdownloadrecord_repository
):
    mock_dsdownloadrecord_repository.create.side_effect = Exception("IntegrityError: download_cookie cannot be null")

    with pytest.raises(Exception, match="IntegrityError: download_cookie cannot be null"):
        download_service.create(
            user_id=1,
            dataset_id=3,
            download_date=FIXED_TIME,
            download_cookie=None,
        )
        
    mock_dsdownloadrecord_repository.create.assert_called_once()

def test_get_dataset_leaderboard_success(
    dataset_service,
    mock_dsdownloadrecord_repository
):
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        assert_called_once_with(period=period)
    assert len(leaderboard_data) == 3


def test_get_dataset_leaderboard_with_month_period(
        dataset_service, mock_dsdownloadrecord_repository):
    period = "month"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        assert_called_once_with(period=period)
    assert len(leaderboard_data) == 3


def test_get_dataset_leaderboard_invalid_period(dataset_service):
    with pytest.raises(ValueError,
                       match="Periodo no soportado: usa 'week' o 'month'"):
        dataset_service.get_dataset_leaderboard(period="invalid_period")


def test_get_dataset_leaderboard_empty(
    dataset_service,
    mock_dsdownloadrecord_repository
):
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        return_value = []
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert len(leaderboard_data) == 0


def test_get_dataset_leaderboard_with_same_downloads(
        dataset_service, mock_dsdownloadrecord_repository):
    mock_dataset_1 = MagicMock(spec=DataSet, id=1, downloads=20)
    mock_dataset_2 = MagicMock(spec=DataSet, id=2, downloads=20)
    mock_dataset_3 = MagicMock(spec=DataSet, id=3, downloads=20)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        return_value = [mock_dataset_1, mock_dataset_2, mock_dataset_3]
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert leaderboard_data[0].id <= leaderboard_data[1].id <= \
           leaderboard_data[2].id


def test_get_dataset_leaderboard_already_sorted(dataset_service,
                                                mock_dsdownloadrecord_repository):
    mock_dataset_1 = MagicMock(spec=DataSet, id=1, downloads=30)
    mock_dataset_2 = MagicMock(spec=DataSet, id=2, downloads=20)
    mock_dataset_3 = MagicMock(spec=DataSet, id=3, downloads=10)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        return_value = [mock_dataset_1, mock_dataset_2, mock_dataset_3]
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert leaderboard_data[0].downloads > \
           leaderboard_data[1].downloads > leaderboard_data[2].downloads


def test_get_dataset_leaderboard_large_number_of_datasets(
        dataset_service, mock_dsdownloadrecord_repository):
    mock_datasets = [MagicMock(spec=DataSet, id=i, downloads=100)
                     for i in range(1000)]
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        return_value = mock_datasets[:3]
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert len(leaderboard_data) == 3


def test_get_dataset_leaderboard_with_null_data(dataset_service,
                                                mock_dsdownloadrecord_repository):
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.\
        return_value = None
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert leaderboard_data is None


def test_get_dataset_leaderboard_limit_parameter(dataset_service, mock_dsdownloadrecord_repository):
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.return_value = []
    period = "week"

    dataset_service.dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week(period=period, limit=1)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.assert_called_once_with(period=period, limit=1)


def test_get_dataset_leaderboard_with_duplicate_datasets(dataset_service, mock_dsdownloadrecord_repository):
    mock_dataset = MagicMock(spec=DataSet, id=1, downloads=10)
    mock_datasets = [mock_dataset, mock_dataset, mock_dataset]
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.return_value = mock_datasets

    leaderboard_data = dataset_service.get_dataset_leaderboard(period="week")

    assert all(d.id == 1 for d in leaderboard_data)


def test_get_dataset_leaderboard_repository_error(dataset_service, mock_dsdownloadrecord_repository):
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.side_effect = Exception("DB error")

    with pytest.raises(Exception, match="DB error"):
        dataset_service.get_dataset_leaderboard(period="week")


def test_get_dataset_leaderboard_with_single_dataset(dataset_service, mock_dsdownloadrecord_repository):
    mock_dataset_1 = MagicMock(spec=DataSet, id=1, downloads=100)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.return_value = [mock_dataset_1]
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert len(leaderboard_data) == 1
    assert leaderboard_data[0].downloads == 100


def test_get_dataset_leaderboard_with_null_values_in_dataset(dataset_service, mock_dsdownloadrecord_repository):
    mock_dataset_1 = MagicMock(spec=DataSet, id=1, downloads=None)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.return_value = [mock_dataset_1]
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert leaderboard_data[0].downloads is None


def test_get_dataset_leaderboard_with_empty_fields(dataset_service, mock_dsdownloadrecord_repository):
    mock_dataset_1 = MagicMock(spec=DataSet, id=1, downloads=100, description=None)
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.return_value = [mock_dataset_1]
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert leaderboard_data[0].description is None


def test_get_dataset_leaderboard_with_invalid_dataset_id(dataset_service, mock_dsdownloadrecord_repository):
    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.return_value = []
    period = "week"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)
    assert leaderboard_data == []


def test_get_dataset_leaderboard_with_special_characters_in_period(dataset_service, mock_dsdownloadrecord_repository):
    period = "week$"
    leaderboard_data = dataset_service.get_dataset_leaderboard(period=period)

    mock_dsdownloadrecord_repository.top_3_dowloaded_datasets_per_week.assert_called_once_with(period="week")

    assert len(leaderboard_data) == 3

#badge feature
@patch("app.modules.badge.routes.get_dataset")
def test_badge_svg_download_success(mock_get_dataset, client, mock_dataset):
    mock_get_dataset.return_value = mock_dataset
    response = client.get("/badge/1.svg")
    
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert f'{mock_dataset["downloads"]} DL' in response.get_data(as_text=True)
    assert response.headers["Content-Disposition"] == 'attachment; filename="badge_1.svg"'
    assert response.headers["Access-Control-Allow-Origin"] == "*"
    assert response.headers["Cache-Control"] == "no-cache"

@patch("app.modules.badge.routes.get_dataset")
def test_badge_svg_download_not_found(mock_get_dataset, client):
    mock_get_dataset.return_value = None
    response = client.get("/badge/999.svg")
    
    assert response.status_code == 404
    assert b"Dataset not found" in response.data

@patch("app.modules.badge.routes.get_dataset")
def test_badge_svg_success(mock_get_dataset, client, mock_dataset):
    mock_get_dataset.return_value = mock_dataset
    response = client.get("/badge/1/svg")
    
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert f'{mock_dataset["downloads"]} DL' in response.get_data(as_text=True)
    assert "Content-Disposition" not in response.headers
    assert response.headers["Access-Control-Allow-Origin"] == "*"

@patch("app.modules.badge.routes.get_dataset")
def test_badge_svg_not_found(mock_get_dataset, client):
    mock_get_dataset.return_value = None
    response = client.get("/badge/999/svg")
    
    assert response.status_code == 404
    assert b"Dataset not found" in response.data

@patch("app.modules.badge.routes.get_dataset")
@patch("app.modules.badge.routes.url_for")
def test_badge_embed_success(mock_url_for, mock_get_dataset, client, mock_dataset):
    mock_get_dataset.return_value = mock_dataset
    mock_url_for.return_value = "http://example.com/badge/1/svg"
    
    response = client.get("/badge/1/embed")
    
    assert response.status_code == 200
    data = response.get_json()
    assert "markdown" in data
    assert "html" in data
    assert mock_dataset["title"] in data["markdown"]
    assert str(mock_dataset["downloads"]) in data["markdown"]
    assert mock_dataset["doi"] in data["markdown"]
    assert "http://example.com/badge/1/svg" in data["html"]

@patch("app.modules.badge.routes.get_dataset")
def test_badge_embed_not_found(mock_get_dataset, client):
    mock_get_dataset.return_value = None
    response = client.get("/badge/999/embed")
    
    assert response.status_code == 404
    data = response.get_json()
    assert data["error"] == "Dataset not found"

def test_make_segment_width_estimation():
    seg = make_segment("Test", "#123456", font_size=10, pad_x=5, min_w=40)
    assert seg["text"] == "Test"
    assert seg["bg"] == "#123456"
    assert seg["w"] >= 40

