package eu.jrie.put.piper.piperhomeservice.api

import eu.jrie.put.piper.piperhomeservice.domain.routine.Routine
import eu.jrie.put.piper.piperhomeservice.domain.routine.RoutinesService
import eu.jrie.put.piper.piperhomeservice.domain.user.asUser
import kotlinx.coroutines.flow.Flow
import org.springframework.http.MediaType.APPLICATION_JSON_VALUE
import org.springframework.security.core.Authentication
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RestController
import reactor.core.publisher.Mono

@RestController
class RoutinesController (
        private val service: RoutinesService
) {
    @GetMapping("/routines", produces = [APPLICATION_JSON_VALUE])
    fun getRoutines(
            auth: Authentication
    ): Flow<Routine> {
        val houseId = auth.asUser().houses.first()
        return service.routinesForHouse(houseId)
    }

    @GetMapping("/routines/{id}", produces = [APPLICATION_JSON_VALUE])
    fun getRoutine(
            @PathVariable id: String,
            auth: Authentication
    ) {

    }

    @PostMapping("/routines", consumes = [APPLICATION_JSON_VALUE], produces = [APPLICATION_JSON_VALUE])
    fun postRoutine(
            @RequestBody routine: Mono<Routine>,
            auth: Authentication
    ) {

    }

    @PutMapping("/routines", consumes = [APPLICATION_JSON_VALUE], produces = [APPLICATION_JSON_VALUE])
    fun putRoutine(
            @RequestBody routine: Mono<Routine>,
            auth: Authentication
    ) {

    }
}
