package com.melsuhaimi.sleepapp.bootstrap.data.persistence

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        SleepSessionEntity::class,
        SleepSignalEntity::class,
        NightOutcomeEntity::class,
        ExpeditionEntity::class,
        ExpeditionPathNodeEntity::class,
        ExpeditionRewardEntity::class,
        PetEntity::class,
        PetProgressionEventEntity::class,
        InventoryStackEntity::class,
        InventoryInstanceEntity::class,
        InventoryTransactionEntity::class,
        EquipmentSlotEntity::class,
        QuestProgressEntity::class,
        QuestObjectiveProgressEntity::class,
        WorldUnlockEntity::class,
        WorldDiscoveryEntity::class,
        CollectionEntryEntity::class,
    ],
    version = SleepDatabase.SCHEMA_VERSION,
    exportSchema = true,
)
abstract class SleepDatabase : RoomDatabase() {
    companion object {
        const val DATABASE_NAME = "sleep_app.db"
        const val SCHEMA_VERSION = 1
    }
}
