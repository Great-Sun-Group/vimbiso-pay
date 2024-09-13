import logging

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, core_service):
        self.core_service = core_service

    def get_state(self):
        return self.core_service.state.get_state(self.core_service.user)

    def update_state(self, new_state, stage, update_from, option):
        logger.info(f"Updating state: stage={stage}, update_from={update_from}, option={option}")
        self.core_service.state.update_state(
            state=new_state,
            stage=stage,
            update_from=update_from,
            option=option
        )

    def reset_state(self):
        logger.info("Resetting state")
        self.core_service.state.reset_state(self.core_service.user)

    def get_current_stage(self):
        return self.core_service.state.stage

    def set_current_stage(self, stage):
        logger.info(f"Setting current stage to: {stage}")
        self.core_service.state.stage = stage

    def get_current_option(self):
        return self.core_service.current_state.get('option')

    def set_current_option(self, option):
        logger.info(f"Setting current option to: {option}")
        self.core_service.current_state['option'] = option

    def get_member_info(self):
        return self.core_service.current_state.get('member', {})

    def update_member_info(self, new_info):
        logger.info("Updating member info")
        if 'member' not in self.core_service.current_state:
            self.core_service.current_state['member'] = {}
        self.core_service.current_state['member'].update(new_info)

    def clear_member_info(self):
        logger.info("Clearing member info")
        self.core_service.current_state['member'] = {}