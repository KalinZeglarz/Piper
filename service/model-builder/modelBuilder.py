from kafka import KafkaConsumer
from pathlib import Path
from requests import post, exceptions, put
from requests.auth import HTTPBasicAuth
from logger import log
import tensorflow as tf
import pandas as pd
import json
import os

HOME_SERVICE_AUTH = HTTPBasicAuth('model-builder', 'secret')
MODELS_BASE_PATH = '/models'  # './models' for local development


class ModelBuilder:
    def __init__(self):
        self.categories_dict = {}
        self.consumer = KafkaConsumer(
            'UserData',
            bootstrap_servers='kafka:9092',
            api_version=(0, 10, 0),
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        log('Model builder initialized')

    def __get_category(self, category_id):
        return self.categories_dict[category_id]

    @staticmethod
    def __split_input_target(chunk):
        input_text = chunk[:-1]
        target_text = chunk[1:]
        return input_text, target_text

    @staticmethod
    def __build_model(vocab_size, embedding_dim, rnn_units, batch_size):
        model = tf.keras.Sequential([
            tf.keras.layers.Embedding(vocab_size, embedding_dim,
                                      batch_input_shape=[batch_size, None]),
            tf.keras.layers.GRU(rnn_units,
                                return_sequences=True,
                                stateful=True,
                                recurrent_initializer='glorot_uniform'),
            tf.keras.layers.Dense(vocab_size)
        ])
        return model

    @staticmethod
    def __loss_function(labels, logits):
        return tf.keras.losses.sparse_categorical_crossentropy(labels, logits, from_logits=True)

    def generate_and_save_model_from_csv(self, model_id, csv_file_path):
        log('Building files structure')
        model_dir = MODELS_BASE_PATH + '/' + model_id + '_model'
        os.makedirs(model_dir, exist_ok=True)

        header_list = ["timestamp", "sensor", "action"]
        sensors_df = pd.read_csv(csv_file_path, names=header_list)

        sensors_df['sensors_with_action'] = sensors_df['sensor'] + '_' + sensors_df['action']

        sensors_df['sensors_with_action_code'] = pd.Categorical(sensors_df['sensors_with_action'])
        categories = pd.Categorical(sensors_df['sensors_with_action_code'])
        CATEGORIES_AMOUNT = len(categories.categories.values)
        log(f'There is {CATEGORIES_AMOUNT} unique categories')

        self.categories_dict = dict(enumerate(sensors_df['sensors_with_action_code'].cat.categories))

        category_dict_file = Path(model_dir + '/category_dict.json')
        category_dict_file.write_text(json.dumps(self.categories_dict, indent=4) + '\n')

        sensors_df['sensors_with_action_code'] = sensors_df.sensors_with_action_code.cat.codes

        dataset_length = len(sensors_df)
        log(f'Event records amount {dataset_length}')

        Y_data = sensors_df.iloc[1:dataset_length]
        Y_data = pd.concat([Y_data, sensors_df.iloc[0:1]], ignore_index=True)
        Y_data = Y_data.reset_index(drop=True)

        new_dataSet = pd.DataFrame()
        new_dataSet['X'] = sensors_df['sensors_with_action_code']
        new_dataSet['Y'] = Y_data['sensors_with_action_code']

        # The maximum length sentence we want for a single input in characters
        seq_length = 100
        examples_per_epoch = len(new_dataSet) // (seq_length + 1)

        sequence_dataset = tf.data.Dataset.from_tensor_slices(sensors_df['sensors_with_action_code'].values)

        sequences = sequence_dataset.batch(seq_length + 1, drop_remainder=True)

        dataset = sequences.map(self.__split_input_target)

        # Batch size
        BATCH_SIZE = 64

        # Buffer size to shuffle the dataset
        # (TF data is designed to work with possibly infinite sequences,
        # so it doesn't attempt to shuffle the entire sequence in memory. Instead,
        # it maintains a buffer in which it shuffles elements).
        if dataset_length > 1000000:
            BUFFER_SIZE = 1000000
        elif dataset_length < 7000:
            raise ValueError(
                "Not enough amount records to train model. Minimum amount is 7000. Recommended amount is 10 000."
            )
        else:
            BUFFER_SIZE = dataset_length

        dataset = dataset.shuffle(BUFFER_SIZE).batch(BATCH_SIZE, drop_remainder=True)

        # Length of the vocabulary (amount of categories)
        vocab_size = CATEGORIES_AMOUNT

        # The embedding dimension
        embedding_dim = 256

        # Number of RNN units
        rnn_units = 1024

        model = self.__build_model(
            vocab_size=vocab_size,
            embedding_dim=embedding_dim,
            rnn_units=rnn_units,
            batch_size=BATCH_SIZE
        )

        for input_example_batch, target_example_batch in dataset.take(1):
            example_batch_predictions = model(input_example_batch)
            print(example_batch_predictions.shape, "# (batch_size, sequence_length, vocab_size)")

        sampled_indices = tf.random.categorical(example_batch_predictions[0], num_samples=1)
        sampled_indices = tf.squeeze(sampled_indices, axis=-1).numpy()

        example_batch_loss = self.__loss_function(target_example_batch, example_batch_predictions)

        model.compile(optimizer='adam', loss=self.__loss_function)
        log('Model compiling optimizer')

        # Directory where the checkpoints will be saved
        checkpoint_dir = model_dir + '/training_checkpoints'
        # Name of the checkpoint files
        checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt_{epoch}")

        checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
            filepath=checkpoint_prefix,
            save_weights_only=True
        )
        log('Model checkpoints created')

        EPOCHS = 10
        history = model.fit(dataset, epochs=EPOCHS, callbacks=[checkpoint_callback])

        tf.train.latest_checkpoint(checkpoint_dir)
        model = self.__build_model(vocab_size, embedding_dim, rnn_units, batch_size=1)
        model.load_weights(tf.train.latest_checkpoint(checkpoint_dir))
        model.build(tf.TensorShape([1, None]))

        log(f'Model building')

        model.save(model_dir)
        log(f'Model has been saved in ${model_dir}\${model_id}_model')

    def run_kafka_data_consumer(self):
        log('Kafka consumer is listening')
        for data_packge in self.consumer:
            log(f'Got {data_packge.value}')
            model_id = data_packge.value['modelId']
            file_path = data_packge.value['path']
            log(f'File submitted as training dataset: {file_path}')

            try:
                self.generate_and_save_model_from_csv(model_id, data_packge.value['path'])
                post(f'https://home-service:80/models/{model_id}/ready', auth=HOME_SERVICE_AUTH, verify=False)
                log(f"Request with {model_id} sent to home-service.")
            except ValueError as value_error:
                log(f"ValueError when building with id: {model_id}: {value_error}")
            except exceptions.ConnectionError:
                log(f"Request to home-service failed, now home-service don't know about model with id: {model_id}")

            try:
                put('http://intelligence-core-service:8004/load-model?', params={'modelId': model_id})
                log(f"Model {model_id} has been loaded asynchronously into intelligence-core-service.")
            except exceptions.ConnectionError:
                log(f"Can't async load model {model_id} into intelligence-core-service service is not available.")


if __name__ == '__main__':
    log('Starting model-builder app')
    mb = ModelBuilder()
    mb.run_kafka_data_consumer()
