import uuid
import json
from typing import Optional
from snowflake.connector import SnowflakeConnection
from app.core.schemas import UserPersonaUpdate
from app.core.logging_conf import get_logger

logger = get_logger("app.repository.persona")

class PersonaRepository:
    """
    Handles all Snowflake persistence for user personas.
    Utilizes Snowflake VARIANT columns for flexible JSON storage of weights.
    """

    @staticmethod
    def upsert_persona(conn: SnowflakeConnection, data: UserPersonaUpdate) -> str:
        """
        Performs a MERGE (upsert) into the user_personas table.
        Ensures a user only has one active persona profile from the cold-start extraction.
        """
        persona_id = str(uuid.uuid4())
        
        # Convert Pydantic dict weights to JSON string for Snowflake VARIANT support
        weights_json = json.dumps(data.explicit_category_weights)
        
        query = """
        MERGE INTO user_personas AS target
        USING (SELECT 
            %s AS user_id, 
            %s AS linkedin_url, 
            %s AS job_title, 
            %s AS seniority, 
            %s AS persona_archetype,
            %s AS bio_summary, 
            PARSE_JSON(%s) AS explicit_weights
        ) AS source
        ON target.user_id = source.user_id
        WHEN MATCHED THEN
            UPDATE SET 
                linkedin_url = source.linkedin_url,
                job_title = source.job_title,
                seniority = source.seniority,
                persona_archetype = source.persona_archetype,
                bio_summary = source.bio_summary,
                explicit_category_weights = source.explicit_weights,
                updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
            INSERT (id, user_id, linkedin_url, job_title, seniority, persona_archetype, bio_summary, explicit_category_weights)
            VALUES (%s, source.user_id, source.linkedin_url, source.job_title, source.seniority, source.persona_archetype, source.bio_summary, source.explicit_weights);
        """
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, (
                data.user_id,
                data.linkedin_url,
                data.job_title,
                data.seniority,
                data.persona_archetype,
                data.bio_summary,
                weights_json,
                persona_id
            ))
            logger.info("Successfully upserted persona to Snowflake", user_id=data.user_id)
            return persona_id
        except Exception as e:
            logger.error("Snowflake UPSERT failure", user_id=data.user_id, error=str(e))
            raise RuntimeError(f"Database sync failed: {str(e)}")

    @staticmethod
    def get_persona(conn: SnowflakeConnection, user_id: str) -> Optional[dict]:
        """
        Fetches the user's explicit and behavioral persona details from Snowflake.
        """
        query = """
        SELECT job_title, seniority, persona_archetype, bio_summary, explicit_category_weights, behavioral_category_weights
        FROM user_personas
        WHERE user_id = %s
        """
        try:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            
            if result:
                persona_data = {
                    "job_title": result[0],
                    "seniority": result[1],
                    "persona_archetype": result[2],
                    "bio_summary": result[3],
                    "explicit_category_weights": json.loads(result[4]) if result[4] else {},
                    "behavioral_category_weights": json.loads(result[5]) if result[5] else {}
                }
                logger.info("Successfully fetched persona", user_id=user_id)
                return persona_data
            
            logger.warning("No persona found for user", user_id=user_id)
            return None
        except Exception as e:
            logger.error("Failed to fetch persona", user_id=user_id, error=str(e))
            return None
