from django.apps import AppConfig


class RekognitionConfig(AppConfig):
    name = 'rekognition'


d = {

    "data": {

        "featureExport": [

            {

                "guid":"cc6135f2-66fa-4195-761c-acb9720e7ecb",
                "market_name":"CORN_NA_SUMMER",
                "feature_name":"ET",
                "feature_level":"TRIAL",
                "last_modified":"2020-01-21 00:00:00",
                "year": 2019,
                "source_id":"19SUDLYG5636201",
                "source":"SPIRIT",
                "value": "ET11",
                "value_type":"varchar",
                "deleted": null

            },

            {
                "guid":"e816d7d8-6ffe-5379-0de2-e080fafb6b92",
                "market_name":"CORN_NA_SUMMER",
                "feature_name":"ACZ",
                "feature_level":"TRIAL",
                "last_modified":"2020-01-21 00:00:00",
                "year": 2019,
                "source_id":"19SUDLYG5636201",
                "source":"SPIRIT",
                "value":"TMP08_non-irrigated",
                "value_type":"varchar",
                "deleted": null
            }

        ]

    }

}
