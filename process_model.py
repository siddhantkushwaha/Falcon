import os

import pandas as pd

import params
from ai.model import Model


def train():
    pt = os.path.join(params.project_root_dir, 'dataset', 'data.csv')
    labels = [
        'primary',
        'spam',
        'transaction',
        'update',
        'verification'
    ]

    falcon_model = Model()

    # ------ Training and saving the model ------
    falcon_model.build_data(labels, pt)
    falcon_model.train(
        vocab_size=5000,
        split_ratio=0.9
    )
    falcon_model.save_model()


def test():
    falcon_model = Model()
    falcon_model.load_model()

    pt = os.path.join(params.project_root_dir, 'dataset', 'data.csv')
    data = pd.read_csv(pt)

    count = 0
    for i, row in data.iterrows():
        label_og = row['Type'].lower()
        label, probabilities = falcon_model.predict(
            unsubscribe=row['Unsubscribe'],
            sender=row['Sender'],
            subject=row['Subject'],
            text=row['Text'],
            files=row['Files']
        )

        if label != label_og:
            count += 1
            print(count, label, label_og)
            print(row)
            print(probabilities, falcon_model.classes)
            print()


if __name__ == '__main__':
    # run training instructions
    train()

    # load model and test
    test()
