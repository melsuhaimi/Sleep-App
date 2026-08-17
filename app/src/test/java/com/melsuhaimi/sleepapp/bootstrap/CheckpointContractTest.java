package com.melsuhaimi.sleepapp.bootstrap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

import org.junit.Test;

public final class CheckpointContractTest {
    @Test
    public void applicationIdentityIsStable() {
        assertEquals("com.melsuhaimi.sleepapp.bootstrap", CheckpointContract.APPLICATION_ID);
        assertEquals("Sleep App APK Bootstrap", CheckpointContract.SCREEN_TEXT);
        assertFalse(CheckpointContract.APPLICATION_ID.isBlank());
    }
}
