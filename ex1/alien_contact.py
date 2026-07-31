from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, ValidationError, model_validator


class ContactType(Enum):
    RADIO = "radio"
    VISUAL = "visual"
    PHYSICAL = "physical"
    TELEPATHIC = "telepathic"


class AlienContact(BaseModel):
    contact_id: str = Field(min_length=5, max_length=15)
    timestamp: datetime
    location: str = Field(min_length=3, max_length=100)
    contact_type: ContactType
    signal_strength: float = Field(ge=0.0, le=10.0)
    duration_minutes: int = Field(ge=1, le=1440)
    witness_count: int = Field(ge=1, le=1440)
    message_received: str | None = Field(default=None, max_length=500)
    is_verified: bool = Field(default=False)

    @model_validator(mode="after")
    def check_business_rules(self):
        if not self.contact_id.startswith("AC"):
            raise ValueError('contact_id must start with "AC"')
        if self.contact_type == ContactType.PHYSICAL and not self.is_verified:
            raise ValueError("Physical contact reports must be verified")
        if (
            self.contact_type == ContactType.TELEPATHIC
            and self.witness_count < 3
        ):
            raise ValueError(
                "Telepathic contact requires at least 3 witnesses"
            )
        if self.signal_strength > 7.0 and not self.message_received:
            raise ValueError(
                "Strong signals should include a received message"
            )
        return self


def main():

    valid_alien = AlienContact(
        contact_id="AC_2024_001",
        timestamp=datetime.now(UTC),
        contact_type=ContactType.RADIO,
        location="Area 51, Nevada",
        signal_strength=8.5,
        duration_minutes=45,
        witness_count=5,
        message_received="'Greetings from Zeta Reticuli'",
    )
    print(
        "Alien Contact Log Validation\n======================================"
    )
    print("Valid contact report:")
    print(f"ID: {valid_alien.contact_id}")
    print(f"Type: {valid_alien.contact_type}")
    print(f"Location: {valid_alien.location}")
    print(f"Signal: {valid_alien.signal_strength}/10")
    print(f"Duration: {valid_alien.duration_minutes} minutes")
    print(f"Witnesses: {valid_alien.witness_count}")
    print(f"Message: {valid_alien.message_received}")
    try:
        AlienContact(
            contact_id="AC_2024_001",
            timestamp=datetime.now(UTC),
            contact_type=ContactType.TELEPATHIC,
            location="Dunkeraue",
            signal_strength=8.0,
            duration_minutes=45,
            witness_count=2,
            message_received="'Greetings from Zeta Reticuli'",
        )
    except ValidationError as error:
        print("\n======================================")
        print("Expected validation error:")
        print(error.errors()[0]["msg"].replace("Value error, ", ""))


if __name__ == "__main__":
    main()
