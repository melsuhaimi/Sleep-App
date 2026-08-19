package com.melsuhaimi.sleepapp.bootstrap.data.persistence

object InitialRoomTables {
    const val SLEEP_SESSION = "sleep_session"
    const val SLEEP_SIGNAL = "sleep_signal"
    const val NIGHT_OUTCOME = "night_outcome"
    const val EXPEDITION = "expedition"
    const val EXPEDITION_PATH_NODE = "expedition_path_node"
    const val EXPEDITION_REWARD = "expedition_reward"
    const val PET = "pet"
    const val PET_PROGRESSION_EVENT = "pet_progression_event"
    const val INVENTORY_STACK = "inventory_stack"
    const val INVENTORY_INSTANCE = "inventory_instance"
    const val INVENTORY_TRANSACTION = "inventory_transaction"
    const val EQUIPMENT_SLOT = "equipment_slot"
    const val QUEST_PROGRESS = "quest_progress"
    const val QUEST_OBJECTIVE_PROGRESS = "quest_objective_progress"
    const val WORLD_UNLOCK = "world_unlock"
    const val WORLD_DISCOVERY = "world_discovery"
    const val COLLECTION_ENTRY = "collection_entry"

    val all: List<String> = listOf(
        SLEEP_SESSION,
        SLEEP_SIGNAL,
        NIGHT_OUTCOME,
        EXPEDITION,
        EXPEDITION_PATH_NODE,
        EXPEDITION_REWARD,
        PET,
        PET_PROGRESSION_EVENT,
        INVENTORY_STACK,
        INVENTORY_INSTANCE,
        INVENTORY_TRANSACTION,
        EQUIPMENT_SLOT,
        QUEST_PROGRESS,
        QUEST_OBJECTIVE_PROGRESS,
        WORLD_UNLOCK,
        WORLD_DISCOVERY,
        COLLECTION_ENTRY,
    )
}
