from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Foundry(db.Model):
    __tablename__ = "foundry"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    location = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Defect(db.Model):
    __tablename__ = "defects"
    id = db.Column(db.Integer, primary_key=True)
    foundry_id = db.Column(db.Integer, db.ForeignKey('foundry.id'), nullable=False)
    defect_type = db.Column(db.String(100), nullable=False)
    total_rejected = db.Column(db.Integer, nullable=False)
    rejection_rate = db.Column(db.Float, nullable=False)
    reference_period = db.Column(db.String(20), nullable=True)
    comparison_period = db.Column(db.String(20), nullable=True)
    foundry = db.relationship("Foundry", back_populates="defects")

class SandProperty(db.Model):
    __tablename__ = "sand_properties"
    id = db.Column(db.Integer, primary_key=True)
    foundry_id = db.Column(db.Integer, db.ForeignKey('foundry.id'), nullable=False)
    parameter = db.Column(db.String(100), nullable=False)
    value = db.Column(db.Float, nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    foundry = db.relationship("Foundry", back_populates="sand_properties")

class RejectionData(db.Model):
    __tablename__ = "rejection_data"
    id = db.Column(db.Integer, primary_key=True)
    foundry_id = db.Column(db.Integer, db.ForeignKey('foundry.id'), nullable=False)
    defect_id = db.Column(db.Integer, db.ForeignKey('defects.id'), nullable=False)
    total_produced = db.Column(db.Integer, nullable=False)
    rejection_percentage = db.Column(db.Float, nullable=False)
    date_recorded = db.Column(db.DateTime, default=datetime.utcnow)
    foundry = db.relationship("Foundry", back_populates="rejection_data")
    defect = db.relationship("Defect", back_populates="rejection_data")

class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"
    id = db.Column(db.Integer, primary_key=True)
    defect_id = db.Column(db.Integer, db.ForeignKey('defects.id'), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    report_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    defect = db.relationship("Defect", back_populates="analysis_results")

Foundry.defects = db.relationship("Defect", order_by=Defect.id, back_populates="foundry")
Foundry.sand_properties = db.relationship("SandProperty", order_by=SandProperty.id, back_populates="foundry")
Foundry.rejection_data = db.relationship("RejectionData", order_by=RejectionData.id, back_populates="foundry")
Defect.rejection_data = db.relationship("RejectionData", order_by=RejectionData.id, back_populates="defect")
Defect.analysis_results = db.relationship("AnalysisResult", order_by=AnalysisResult.id, back_populates="defect")
