import Axios from 'axios';
import utils from '../../commons/utils';

export const routines = {
  namespaced: true,
  state: {
    routines: [],
    selectedRoutine: {}
  },
  getters: {
    routines: state => state.routines,
    selectedRoutine: state => state.selectedRoutine
  },
  actions: {
    addRoutine({ state }) {
      Axios.post(
        'https://jrie.eu:8001/routines/',
        {
          name: state.selectedRoutine.name,
          enabled: state.selectedRoutine.enabled,
          events: state.selectedRoutine.events,
          configuration: state.selectedRoutine.configuration
        },
        {
          headers: {
            Accept: 'application/json'
          },
          auth: utils.authentication
        }
      )
        .then(res => {
          console.log(res);
        })
        .catch(() => {
          //TODO handle error
        });
    },
    getRoutines({ commit }) {
      Axios.get('https://jrie.eu:8001/routines', {
        headers: {
          Accept: 'application/json'
        },
        auth: utils.authentication
      }).then(res => {
        commit('SET_ROUTINES', res.data.routines);
      });
    },

    getRoutine({ commit }, id) {
      Axios.get('https://jrie.eu:8001/routines/' + id, {
        headers: {
          Accept: 'application/json'
        },
        auth: utils.authentication
      })
        .then(res => {
          commit('SET_SELECTED_ROUTINE', res.data.routine);
        })
        .catch(() => {
          //TODO handle error
        });
    },

    editRoutine({ state }, id) {
      Axios.put(
        'https://jrie.eu:8001/routines/' + id,
        {
          name: state.selectedRoutine.name,
          enabled: state.selectedRoutine.enabled,
          events: state.selectedRoutine.events,
          configuration: state.selectedRoutine.configuration
        },
        {
          headers: {
            Accept: 'application/json'
          },
          auth: utils.authentication
        }
      )
        .then(res => {
          console.log(res);
        })
        .catch(() => {
          //TODO handle error
        });
    },

    addEventToRoutine({ commit, state }, index) {
      if (!state.selectedRoutine.events) {
        commit('ASSIGN_EVENTS_TO_ROUTINE', [
          {
            deviceId: '',
            eventId: ''
          }
        ]);
      } else {
        let tail = [...state.selectedRoutine.events];
        console.log(tail, index);
        let head = tail.splice(0, index + 1);
        console.log(head);

        commit('ASSIGN_EVENTS_TO_ROUTINE', [
          ...head,
          {
            deviceId: '',
            eventId: ''
          },
          ...tail
        ]);
      }
    },

    setSelectedRoutine({ commit }, routine) {
      commit('SET_SELECTED_ROUTINE', routine);
    },

    setSelectedRoutineEvents({ commit }, events) {
      commit('ASSIGN_EVENTS_TO_ROUTINE', events);
    }
  },
  mutations: {
    SET_ROUTINES(state, routines) {
      state.routines = routines;
    },
    SET_SELECTED_ROUTINE(state, routine) {
      state.selectedRoutine = routine;
    },
    ASSIGN_EVENTS_TO_ROUTINE(state, events) {
      state.selectedRoutine.events = [...events];
    }
  }
};