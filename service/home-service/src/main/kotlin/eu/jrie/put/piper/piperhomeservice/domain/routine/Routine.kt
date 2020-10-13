package eu.jrie.put.piper.piperhomeservice.domain.routine

import eu.jrie.put.piper.piperhomeservice.domain.event.Event
import org.springframework.data.annotation.Id
import org.springframework.data.mongodb.core.mapping.Document
import java.time.DayOfWeek
import java.time.OffsetTime

@Document
data class Routine (
        @Id
        val id: String,
        val houseId: String,
        val modelId: String?,
        val enabled: Boolean,
        val events: List<RoutineEvent>,
        val configuration: RoutineConfiguration?
)

data class RoutineConfiguration (
        val days: List<DayOfWeek> = emptyList(),
        val start: OffsetTime? = null,
        val end: OffsetTime? = null
)

data class RoutineEvent (
        override val trigger: String,
        override val action: String
) : Event
