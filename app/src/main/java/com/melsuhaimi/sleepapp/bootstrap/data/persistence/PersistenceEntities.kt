package com.melsuhaimi.sleepapp.bootstrap.data.persistence

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = InitialRoomTables.SLEEP_SESSION)
data class SleepSessionEntity(
    @PrimaryKey @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "started_at_epoch_millis") val startedAtEpochMillis: Long,
    @ColumnInfo(name = "ended_at_epoch_millis") val endedAtEpochMillis: Long? = null,
    @ColumnInfo(name = "status") val status: String,
)

@Entity(tableName = InitialRoomTables.SLEEP_SIGNAL)
data class SleepSignalEntity(
    @PrimaryKey @ColumnInfo(name = "signal_id") val signalId: String,
    @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "captured_at_epoch_millis") val capturedAtEpochMillis: Long,
    @ColumnInfo(name = "source") val source: String,
    @ColumnInfo(name = "confidence") val confidence: Double,
)

@Entity(tableName = InitialRoomTables.NIGHT_OUTCOME)
data class NightOutcomeEntity(
    @PrimaryKey @ColumnInfo(name = "outcome_id") val outcomeId: String,
    @ColumnInfo(name = "session_id") val sessionId: String,
    @ColumnInfo(name = "sleep_minutes") val sleepMinutes: Int,
    @ColumnInfo(name = "quality_score") val qualityScore: Int,
)

@Entity(tableName = InitialRoomTables.EXPEDITION)
data class ExpeditionEntity(
    @PrimaryKey @ColumnInfo(name = "expedition_id") val expeditionId: String,
    @ColumnInfo(name = "seed") val seed: Long,
    @ColumnInfo(name = "region_id") val regionId: String,
    @ColumnInfo(name = "status") val status: String,
)

@Entity(tableName = InitialRoomTables.EXPEDITION_PATH_NODE)
data class ExpeditionPathNodeEntity(
    @PrimaryKey @ColumnInfo(name = "path_node_id") val pathNodeId: String,
    @ColumnInfo(name = "expedition_id") val expeditionId: String,
    @ColumnInfo(name = "node_id") val nodeId: String,
    @ColumnInfo(name = "step_index") val stepIndex: Int,
)

@Entity(tableName = InitialRoomTables.EXPEDITION_REWARD)
data class ExpeditionRewardEntity(
    @PrimaryKey @ColumnInfo(name = "reward_id") val rewardId: String,
    @ColumnInfo(name = "expedition_id") val expeditionId: String,
    @ColumnInfo(name = "reward_type") val rewardType: String,
    @ColumnInfo(name = "stable_item_id") val stableItemId: String? = null,
    @ColumnInfo(name = "quantity") val quantity: Int,
)

@Entity(tableName = InitialRoomTables.PET)
data class PetEntity(
    @PrimaryKey @ColumnInfo(name = "pet_id") val petId: String,
    @ColumnInfo(name = "species_id") val speciesId: String,
    @ColumnInfo(name = "form_id") val formId: String,
    @ColumnInfo(name = "xp") val xp: Long,
    @ColumnInfo(name = "level") val level: Int,
)

@Entity(tableName = InitialRoomTables.PET_PROGRESSION_EVENT)
data class PetProgressionEventEntity(
    @PrimaryKey @ColumnInfo(name = "event_id") val eventId: String,
    @ColumnInfo(name = "pet_id") val petId: String,
    @ColumnInfo(name = "event_type") val eventType: String,
    @ColumnInfo(name = "created_at_epoch_millis") val createdAtEpochMillis: Long,
)

@Entity(tableName = InitialRoomTables.INVENTORY_STACK)
data class InventoryStackEntity(
    @PrimaryKey @ColumnInfo(name = "stack_id") val stackId: String,
    @ColumnInfo(name = "item_id") val itemId: String,
    @ColumnInfo(name = "quantity") val quantity: Int,
)

@Entity(tableName = InitialRoomTables.INVENTORY_INSTANCE)
data class InventoryInstanceEntity(
    @PrimaryKey @ColumnInfo(name = "instance_id") val instanceId: String,
    @ColumnInfo(name = "item_id") val itemId: String,
    @ColumnInfo(name = "created_at_epoch_millis") val createdAtEpochMillis: Long,
)

@Entity(tableName = InitialRoomTables.INVENTORY_TRANSACTION)
data class InventoryTransactionEntity(
    @PrimaryKey @ColumnInfo(name = "transaction_id") val transactionId: String,
    @ColumnInfo(name = "item_id") val itemId: String,
    @ColumnInfo(name = "delta") val delta: Int,
    @ColumnInfo(name = "reason") val reason: String,
    @ColumnInfo(name = "created_at_epoch_millis") val createdAtEpochMillis: Long,
)

@Entity(tableName = InitialRoomTables.EQUIPMENT_SLOT)
data class EquipmentSlotEntity(
    @PrimaryKey @ColumnInfo(name = "slot_id") val slotId: String,
    @ColumnInfo(name = "slot_type") val slotType: String,
    @ColumnInfo(name = "equipped_instance_id") val equippedInstanceId: String? = null,
)

@Entity(tableName = InitialRoomTables.QUEST_PROGRESS)
data class QuestProgressEntity(
    @PrimaryKey @ColumnInfo(name = "quest_id") val questId: String,
    @ColumnInfo(name = "status") val status: String,
    @ColumnInfo(name = "updated_at_epoch_millis") val updatedAtEpochMillis: Long,
)

@Entity(tableName = InitialRoomTables.QUEST_OBJECTIVE_PROGRESS)
data class QuestObjectiveProgressEntity(
    @PrimaryKey @ColumnInfo(name = "objective_progress_id") val objectiveProgressId: String,
    @ColumnInfo(name = "quest_id") val questId: String,
    @ColumnInfo(name = "objective_id") val objectiveId: String,
    @ColumnInfo(name = "progress_count") val progressCount: Int,
)

@Entity(tableName = InitialRoomTables.WORLD_UNLOCK)
data class WorldUnlockEntity(
    @PrimaryKey @ColumnInfo(name = "unlock_id") val unlockId: String,
    @ColumnInfo(name = "world_id") val worldId: String,
    @ColumnInfo(name = "unlocked_at_epoch_millis") val unlockedAtEpochMillis: Long,
)

@Entity(tableName = InitialRoomTables.WORLD_DISCOVERY)
data class WorldDiscoveryEntity(
    @PrimaryKey @ColumnInfo(name = "discovery_id") val discoveryId: String,
    @ColumnInfo(name = "world_id") val worldId: String,
    @ColumnInfo(name = "discovered_at_epoch_millis") val discoveredAtEpochMillis: Long,
)

@Entity(tableName = InitialRoomTables.COLLECTION_ENTRY)
data class CollectionEntryEntity(
    @PrimaryKey @ColumnInfo(name = "entry_id") val entryId: String,
    @ColumnInfo(name = "collection_id") val collectionId: String,
    @ColumnInfo(name = "stable_content_id") val stableContentId: String,
    @ColumnInfo(name = "unlocked_at_epoch_millis") val unlockedAtEpochMillis: Long,
)
