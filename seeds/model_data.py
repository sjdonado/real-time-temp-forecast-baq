from flask_seeder import Seeder

from app.database import ModelData

class ModelDataSeeder(Seeder):
  def run(self):
    keras_model = ModelData()
    keras_model.path = 'data/model.h5'
    self.db.session.add(keras_model)

    scaler = ModelData()
    scaler.path = 'data/scaler.save'
    self.db.session.add(scaler)

    train_data = ModelData()
    train_data.path = 'data/train_data.csv'
    self.db.session.add(train_data)

    self.db.session.commit()
