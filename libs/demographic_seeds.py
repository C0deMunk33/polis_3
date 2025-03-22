from pydantic import BaseModel
from typing import List, Optional
import random

class DemographicSeed(BaseModel):
    first_name: str
    last_name: str
    state: str
    age: int
    birthdate: str
    sex: str
    race: str
    is_student: bool
    education: str
    is_in_labor_force: bool
    is_employed: bool
    occupation_category: Optional[str] = None
    hobbies: List[str]
    aspirations: List[str]
    values: List[str]

    # formatted description
    def get_formatted_description(self):
        return f"Name: {self.first_name} {self.last_name}\nState: {self.state}\nAge: {self.age}\nBirthdate: {self.birthdate}\nSex: {self.sex}\nRace: {self.race}\nEducation: {self.education}\nIs Student: {self.is_student}\nIs in Labor Force: {self.is_in_labor_force}\nIs Employed: {self.is_employed}\nOccupation Category: {self.occupation_category}\nHobbies: {self.hobbies}\nAspirations: {self.aspirations}\nValues: {self.values}"

class DemographicSeedManager:
    def __init__(self, seed_file_path: str = "./data/synthetic_demographics.jsonl"):
        self.seed_file_path = seed_file_path

    def get_demographic_seed_by_index(self, index: int):
        with open(self.seed_file_path, "r") as f:
            line_idx = 0
            for line in f:
                if line_idx == index:
                    return DemographicSeed.model_validate_json(line)
                line_idx += 1
            return None
    
    def get_random_demographic_seed(self):
        with open(self.seed_file_path, "r") as f:
            lines = f.readlines()
            return DemographicSeed.model_validate_json(lines[random.randint(0, len(lines) - 1)])


