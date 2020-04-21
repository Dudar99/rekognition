import boto3
import json
import sys
import time


def get_bucket_and_key(event):
    event_rec = event['Records'] and event['Records'][0]
    bucket_name = event_rec['s3']['bucket']['name']
    video_name = event_rec['s3']['object']['key']
    return bucket_name, video_name


def get_name_suffix() -> str:
    return str(int(round(time.time() * 1000)))


class VideoDetect:
    job_id = ''
    rek = boto3.client('rekognition')
    sqs = boto3.client('sqs')
    sns = boto3.client('sns')

    roleArn = ''
    bucket = ''
    video = ''
    start_job_id = ''

    sqs_queue_url = ''
    sns_topic_arn = ''
    processType = ''

    matched_faces = []

    def __init__(self, role, bucket, video):
        self.roleArn = role
        self.bucket = bucket
        self.video = video

    def get_sqs_message_success(self):

        job_found = False
        succeeded = False

        dotLine = 0
        while not job_found:
            sqs_response = self.sqs.receive_message(QueueUrl=self.sqs_queue_url, MessageAttributeNames=['ALL'],
                                                    MaxNumberOfMessages=10)

            if sqs_response:

                if 'Messages' not in sqs_response:
                    if dotLine < 40:
                        print('.', end='')
                        dotLine = dotLine + 1
                    else:
                        print()
                        dotLine = 0
                    sys.stdout.flush()
                    time.sleep(5)
                    continue

                for message in sqs_response['Messages']:
                    notification = json.loads(message['Body'])
                    rekMessage = json.loads(notification['Message'])
                    print(rekMessage['JobId'])
                    print(rekMessage['Status'])
                    if rekMessage['JobId'] == self.start_job_id:
                        print('Matching Job Found:' + rekMessage['JobId'])
                        job_found = True
                        if (rekMessage['Status'] == 'SUCCEEDED'):
                            succeeded = True

                        self.sqs.delete_message(QueueUrl=self.sqs_queue_url,
                                                ReceiptHandle=message['ReceiptHandle'])
                    else:
                        print("Job didn't match:" +
                              str(rekMessage['JobId']) + ' : ' + self.start_job_id)
                    # Delete the unknown message. Consider sending to dead letter queue
                    self.sqs.delete_message(QueueUrl=self.sqs_queue_url,
                                            ReceiptHandle=message['ReceiptHandle'])

        return succeeded

    def start_face_detection(self):
        response = self.rek.start_face_search(Video={'S3Object': {'Bucket': self.bucket, 'Name': self.video}},
                                              NotificationChannel={
                                                  'RoleArn': self.roleArn,
                                                  'SNSTopicArn': self.sns_topic_arn},
                                              CollectionId="faces",
                                              )

        self.start_job_id = response['JobId']
        print('Start Job Id: ' + self.start_job_id)

    def get_face_detection_results(self):
        maxResults = 10
        paginationToken = ''
        finished = False
        matched_faces = []
        print("start detecting...")
        while not finished:
            response = self.rek.get_face_search(JobId=self.start_job_id,
                                                MaxResults=maxResults,
                                                NextToken=paginationToken,
                                                SortBy='TIMESTAMP')
            print(response)
            if not response['JobStatus'] == 'SUCCEEDED':
                print('Video is  still processing..')
                time.sleep(5)
                continue

            print('Codec: ' + response['VideoMetadata']['Codec'])
            print('Duration: ' + str(response['VideoMetadata']['DurationMillis']))
            print('Format: ' + response['VideoMetadata']['Format'])
            print('Frame rate: ' + str(response['VideoMetadata']['FrameRate']))
            print()

            for prs in response['Persons']:
                person = prs['Person']
                print("Timestamp: " + str(prs['Timestamp']))
                print("   Person: " + str(person))
                print('Face matches:', prs['FaceMatches'])
                matched_faces.append({'person_index': person['Index'], 'face_match': prs['FaceMatches']})

                if 'NextToken' in response:
                    paginationToken = response['NextToken']
                else:
                    finished = True
        self.matched_faces = matched_faces

    def get_top_matched_faces(self):
        faces = []
        res = {}
        for prs in self.matched_faces:
            for fc_mtch in prs.get('face_match'):
                faces.append(
                    {'similarity': fc_mtch['Similarity'],
                     'face_id': fc_mtch['Face']['FaceId']
                     }
                )
        for face in faces:
            if face['face_id'] in res:
                if face['similarity'] > res[face['face_id']]:
                    res[face['face_id']] = face['similarity']
            else:
                res.update({face['face_id']: face['similarity']})
        # TODO make it via class field and
        print(res)
        return res

    def create_topic(self):

        # Create SNS topic

        sns_topic_name = "AmazonRekognitionExample" + get_name_suffix()

        topic_response = self.sns.create_topic(Name=sns_topic_name)

        # set sns topic for results posting
        self.sns_topic_arn = topic_response['TopicArn']

    def create_queue(self):
        # create SQS queue
        sqs_queue_name = "AmazonRekognitionQueue" + get_name_suffix()
        self.sqs.create_queue(QueueName=sqs_queue_name)
        self.sqs_queue_url = self.sqs.get_queue_url(QueueName=sqs_queue_name)['QueueUrl']

        attributes = self.sqs.get_queue_attributes(QueueUrl=self.sqs_queue_url,
                                                   AttributeNames=['QueueArn'])['Attributes']

        sqs_queue_arn = attributes['QueueArn']

        # Subscribe SQS queue to SNS topic
        self.sns.subscribe(
            TopicArn=self.sns_topic_arn,
            Protocol='sqs',
            Endpoint=sqs_queue_arn)

        # Authorize SNS to write SQS queue
        policy = """{{
              "Version":"2012-10-17",
              "Statement":[
                {{
                  "Sid":"MyPolicy",
                  "Effect":"Allow",
                  "Principal" : {{"AWS" : "*"}},
                  "Action":"SQS:SendMessage",
                  "Resource": "{}",
                  "Condition":{{
                    "ArnEquals":{{
                      "aws:SourceArn": "{}"
                    }}
                  }}
                }}
              ]
            }}""".format(sqs_queue_arn, self.sns_topic_arn)

        response = self.sqs.set_queue_attributes(
            QueueUrl=self.sqs_queue_url,
            Attributes={
                'Policy': policy
            })

    def delete_topic_and_queue(self):
        self.sqs.delete_queue(QueueUrl=self.sqs_queue_url)
        self.sns.delete_topic(TopicArn=self.sns_topic_arn)

    def __subscribe_to_email(self, email: str):
        print("Subscribing SNS to send emails")
        response = self.sns.subscribe(
            TopicArn=self.sns_topic_arn,
            Protocol='email',
            Endpoint=email,

            ReturnSubscriptionArn=True | False
        )
        print(f"Subscribing response:{response}")

    def publish_results_to_sns(self, recs):

        self.__subscribe_to_email(email="yurii_dudar@epam.com")
        self.sns.publish(
            TopicArn="arn:aws:sns:us-east-1:573200067457:mytopic",#self.sns_topic_arn,
            # PhoneNumber='+380971237965',
            Message=''.join(str(recs)),
            Subject='Students',

        )


def lambda_handler(event, context):
    print("Test event: ", event)
    bucket_name, video_name = get_bucket_and_key(event)
    # TODO make role dynamically (may be using serverless framework)
    role_arn = 'arn:aws:iam::573200067457:role/rekognition-dev123-us-east-1-lambdaRole'

    analyzer = VideoDetect(role_arn, bucket_name, video_name)
    analyzer.create_topic()
    analyzer.create_queue()

    analyzer.start_face_detection()
    # if analyzer.get_sqs_message_success():
    # TODO remove this sleep and add SNS and SQS or Lambda handler for matched faces handling

    analyzer.get_face_detection_results()
    response = analyzer.get_top_matched_faces()
    analyzer.publish_results_to_sns(response)
    time.sleep(10)
    # analyzer.delete_topic_and_queue()

    return "Finishing..."
